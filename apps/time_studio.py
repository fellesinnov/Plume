"""Streamlit-only TIME-1B/C widgets over headless Plume history/runner contracts.

Only presentation/navigation happens here. No density, sampling, Copernicus
science or permit logic is calculated in the app.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import streamlit as st

from plume.errors import PlumeError
from plume.history import acquire_history
from plume.ocean import history_panel, render_ocean_panel
from plume.runner import (load_historical_run, preflight_history,
                          restored_forcing_config, run_history)


def map_point_selector(*, latitude: float, longitude: float) -> tuple[float, float]:
    """Click WGS84 point during new-project creation; exact coordinates win."""
    lat = float(st.session_state.get("new_site_lat", latitude))
    lon = float(st.session_state.get("new_site_lon", longitude))
    with st.expander("Select a point on the map (optional)", expanded=False):
        try:
            import folium
            from streamlit_folium import st_folium
        except ImportError:
            st.info("Interactive map requires the Studio optional packages; latitude/longitude entry still works.")
        else:
            chart = folium.Map(location=[lat, lon], zoom_start=8, control_scale=True)
            folium.CircleMarker([lat, lon], radius=6, color="cyan", fill=True).add_to(chart)
            selection = st_folium(chart, height=340, use_container_width=True,
                                  returned_objects=["last_clicked"], key="new_site_map")
            point = selection.get("last_clicked") if selection else None
            if point is not None:
                lat, lon = float(point["lat"]), float(point["lng"])
                current_click = (lat, lon)
                # Only apply a NEW click. Preserving an old last_clicked must
                # not overwrite a subsequent deliberate numeric edit.
                if current_click != st.session_state.get("new_site_last_click"):
                    st.session_state["new_site_last_click"] = current_click
                    st.session_state["new_site_lat"] = lat
                    st.session_state["new_site_lon"] = lon
                    st.session_state["create_project_lat"] = lat
                    st.session_state["create_project_lon"] = lon
            st.caption("Click a location to propose its coordinates; the numeric fields below may override it.")
    return lat, lon


def _time_config(project, store):
    return restored_forcing_config(project, store) if project.is_locked else project.config


def ocean_stage(project, store) -> None:
    st.subheader("Ocean · Historical profiles and selected UTC hour")
    cfg = _time_config(project, store)
    lat, lon = cfg.normalized["site"]["latitude_deg"], cfg.normalized["site"]["longitude_deg"]
    st.caption(f"WGS84 project site {lat:.5f}°N, {lon:.5f}°E | depth "
               f"{cfg.normalized['site']['water_depth_m']:g} m. "
               "History acquisition is explicit. Geometry edits reuse its cache.")
    st.map({"lat": [lat], "lon": [lon]}, zoom=9)
    st.caption("For a different site, create a new Project using the interactive map. "
               "Changing a locked site's coordinates requires a new design revision.")
    specs = cfg.normalized["forcing"]["ambient"]
    if any(v["provider"] == "copernicus" for v in specs.values()):
        st.info("Copernicus access uses local account settings. Exact wet-cell fallback, native "
                "temperature conversion and incomplete hours are recorded in provider provenance.")
    if st.button("Load ocean history / reuse workspace cache", type="primary"):
        try:
            history = acquire_history(cfg, workspace_override=store.root)
            st.session_state["history"] = history
            st.session_state["historical_config_identity"] = cfg.sha256
            st.session_state.pop("history_selected_clock", None)
            st.success(("Disk cache hit" if history.cache_hit else "Acquired and cached inputs") +
                       f" · {len(history.available_times)}/{len(history.clock_times)} UTC steps complete")
        except (PlumeError, OSError) as exc:
            st.error(str(exc))
    history = st.session_state.get("history")
    if history is None:
        st.info("Load an environmental history, or use the original one-hour snapshot workflow when providers are static.")
        return
    try:
        history._require_config(cfg)
        history.verify_identity()
    except PlumeError as exc:
        st.warning(f"Previously loaded history is stale for this project: {exc}. Acquire again.")
        return
    st.caption(f"History SHA {history.data_sha256[:16]} | {len(history.available_times)} complete "
               f"/ {len(history.clock_times)} requested | {len(history.missing_by_time)} missing. "
               "No interpolation of missing hours.")
    if history.missing_by_time:
        with st.expander("Missing timestamps and provider names"):
            st.dataframe([{"UTC": t, "Missing": ", ".join(names)}
                          for t,names in list(history.missing_by_time.items())[:100]],
                         use_container_width=True, hide_index=True)
    choice = st.selectbox("History diagnostic", ["temperature", "salinity", "u_east", "v_north"],
                          format_func={"temperature":"In-situ temperature [°C]",
                                       "salinity":"Practical salinity [PSU]",
                                       "u_east":"Eastward current [m/s]",
                                       "v_north":"Northward current [m/s]"}.get)
    selected = st.selectbox("Exact available design timestamp [UTC]", history.available_times,
                            key="history_selected_clock")
    try:
        panel = history_panel(history, quantity=choice)
        fig = render_ocean_panel(panel, selected=selected)
        st.pyplot(fig, use_container_width=True)
        from matplotlib import pyplot as plt
        plt.close(fig)
    except (PlumeError, ValueError) as exc:
        st.error(f"Ocean diagnostic unavailable: {exc}")
    if st.button("Pin selected UTC ocean state for Design"):
        try:
            pinned = history.snapshot_at(cfg, selected)
            st.session_state["snapshot"] = pinned
            st.session_state["evaluations"] = {}
            st.session_state["comparisons"] = []
            st.success(f"Pinned {selected} · {pinned.snapshot_sha256[:16]}; changing outlet geometry does not refetch")
        except PlumeError as exc:
            st.error(str(exc))
    pinned = st.session_state.get("snapshot")
    if pinned is not None:
        st.caption(f"Current Design snapshot: {pinned.at_utc} · {pinned.snapshot_sha256[:16]}")
        with st.expander("Exact selected source and ambient provenance"):
            st.json(pinned.providers)
        if pinned.current_profile_east_north_mps is not None:
            st.caption("Vertically varying current retained in the pinned MODEL-1 state (ENU m/s).")


def simulate_stage(project, store) -> None:
    st.subheader("Simulate · Bounded quasi-steady near-field replay")
    st.warning("UNVALIDATED thermal model. This run produces sampled near-field indicators, "
               "NOT legal permit pass/fail, calibrated physics, or a far-field circulation prediction.")
    if not project.is_locked:
        st.info("First save and lock a design revision in Design.")
        return
    history = st.session_state.get("history")
    if history is None:
        st.info("Return to Ocean and Load history before running the locked design.")
        return
    try:
        pf = preflight_history(project, store, history)
    except PlumeError as exc:
        st.error(f"Preflight HOLD: {exc}. Reacquire history for the original plant source, not locked constants.")
        return
    st.write(f"Revision `{pf.locked_revision_id}` · {pf.clock_steps} UTC slots · "
             f"{pf.available_steps} with full forcing · {pf.missing_steps} missing")
    for w in pf.warnings:
        st.caption(w)
    limit = st.number_input("First N chronological forcing slots to simulate", min_value=1,
                            max_value=pf.clock_steps, value=min(3,pf.clock_steps), step=1)
    st.caption("Default three steps for a quick mechanical smoke. A year can involve 8,760 "
               "independent model runs; processing time can be substantial. "
               "Missing steps remain explicit and are not simulated.")
    keep = st.checkbox("Save a computed PNG for the highest sampled section peak", value=False)
    if st.button("Run selected historical steps", type="primary"):
        try:
            with st.spinner("Running actual MODEL-1 → FIELD-1 for selected exact UTC states…"):
                run = run_history(project, store, history, max_steps=int(limit),
                                  retain_example_fields=keep)
            st.session_state["selected_time_run"] = run.run_id
            st.success(f"Run saved to ignored workspace: {run.run_id}")
            st.json(run.summary)
        except (PlumeError, RuntimeError, ValueError, OSError) as exc:
            st.error(f"Historical run FAILED (not silently skipped): {exc}")


def results_stage(project) -> None:
    st.subheader("Results · Recorded near-field indicators")
    st.warning("UNVALIDATED / NOT_ASSESSED: section/plan grid-slice metrics, not 3-D mixing-zone "
               "compliance, receptor findings or formal permit criteria.")
    folder = project.project_dir / "runs"
    names = sorted((p.name for p in folder.glob("time1-*") if p.is_dir()), reverse=True)
    if not names:
        st.info("No TIME-1C history runs saved yet. Go to Simulate after locking a design.")
        return
    selected = st.selectbox("Saved local historical run", names,
                            index=names.index(st.session_state["selected_time_run"])
                            if st.session_state.get("selected_time_run") in names else 0)
    try:
        run = load_historical_run(project, selected)
        manifest = run.manifest
        if manifest["project"]["locked_revision_id"] != project.locked_revision_id:
            st.warning("STALE for current project: this output belongs to a different locked design revision.")
        st.json(run.summary)
        import json
        rows = json.loads((run.path / "timestep_metrics.json").read_text(encoding="utf-8"))["rows"]
        st.dataframe(rows, hide_index=True, use_container_width=True)
        from pandas import DataFrame
        frame = DataFrame([{ "UTC": r["time_utc"], "Section peak ΔT [°C]":r["section_peak_delta_T_C"],
                             "Plan peak ΔT [°C]":r["plan_peak_delta_T_C"]} for r in rows])
        frame = frame.set_index("UTC")
        st.line_chart(frame)
        img = run.path / "selected-field.png"
        if img.exists():
            st.image(str(img), caption="Worst sampled near-field section/plan: UNVALIDATED")
        st.caption(f"Run manifest: {run.path / 'manifest.json'} · input history SHA "
                   f"{manifest['forcing']['history_data_sha256'][:16]}")
    except (PlumeError, OSError, ValueError, KeyError) as exc:
        st.error(f"Results cannot be loaded: {exc}")
