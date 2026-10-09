"""Plume Design Studio / DESIGN-1 Streamlit shell.

Run: pip install -e '.[studio]'; streamlit run apps/design_studio.py
All physics, provider loading, normalization, revision IO and metrics live under
plume.design; this file only binds widgets to that headless API.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import streamlit as st

from plume.design import (
    ProjectStore, candidate_config, evaluate_design, export_portable_yaml,
    export_snapshot_yaml, pin_snapshot,
)
from plume.config import load_config
from plume.errors import PlumeError
from plume.render import render_field_pair

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Plume · Design Studio", page_icon="🌊", layout="wide")
st.markdown("""
<style>
  .stApp {background: #0b1520; color: #e6edf5;}
  [data-testid="stSidebar"] {background: #0e2030;}
  [data-testid="stMetric"] {background: #132638; border: 1px solid #284356;
      border-radius: 11px; padding: 14px 18px;}
  [data-testid="stMetricLabel"] {color: #b5cbd7;}
  h1,h2,h3 {letter-spacing: -.025em;}
</style>
""", unsafe_allow_html=True)


def _workspace() -> Path:
    default = os.getenv("PLUME_WORKSPACE", str(ROOT / "workspace"))
    return Path(st.sidebar.text_input("Local workspace", value=default)).expanduser().resolve()


def _reset_project(project_id: str, workspace_root: Path) -> None:
    # A project ID is only unique *within* its workspace. Switching workspaces
    # must not carry a pinned environmental column or design cache across sites.
    key = (str(workspace_root.resolve()), project_id)
    if st.session_state.get("loaded_id") != key:
        st.session_state["loaded_id"] = key
        st.session_state.pop("snapshot", None)
        st.session_state.pop("evaluations", None)
        st.session_state.pop("comparisons", None)
        st.session_state.pop("snapshot_clock", None)
        for key in list(st.session_state):
            if key.startswith("design_control_"):
                del st.session_state[key]


def _new_project(store: ProjectStore) -> None:
    with st.form("new-project"):
        st.subheader("Start a project")
        template_path = st.text_input("Source config (YAML/JSON)",
                                      value=str(ROOT / "configs" / "example.yaml"))
        c1, c2 = st.columns(2)
        with c1:
            pid = st.text_input("Project ID", value="site_study")
            lat = st.number_input("Latitude [°N]", value=60.0, min_value=-90.0, max_value=90.0)
        with c2:
            name = st.text_input("Project name", value="Site study")
            lon = st.number_input("Longitude [°E]", value=5.0, min_value=-180.0, max_value=180.0)
        if st.form_submit_button("Create workspace project", type="primary"):
            try:
                cfg = load_config(template_path)
                created = store.create(cfg, project_id=pid, name=name,
                                       latitude_deg=lat, longitude_deg=lon)
                st.session_state["next_project"] = created.project_id
                st.rerun()
            except (PlumeError, OSError) as exc:
                st.error(str(exc))


def _ocean(project):
    st.subheader("Ocean · Pin a local environmental snapshot")
    st.caption("DESIGN-1 loads inline or local CSV depth profiles. Copernicus history, map selection "
               "and date ranking arrive in TIME-1. Loading occurs only when you press Pin.")
    source = project.config.normalized["forcing"]
    at_start = source["clock"]["start"]
    timestamp = st.text_input("Design snapshot timestamp (UTC, ISO 8601)",
                              value=at_start, key="snapshot_clock")
    if st.button("Pin environmental snapshot", type="primary"):
        try:
            st.session_state["snapshot"] = pin_snapshot(project.config, at_utc=timestamp)
            st.session_state["evaluations"] = {}
            st.session_state["comparisons"] = []
            st.success("Snapshot pinned locally. Changing a design control will not reload providers.")
        except (PlumeError, OSError) as exc:
            st.error(str(exc))
    snapshot = st.session_state.get("snapshot")
    if snapshot is None:
        st.info("Pin a snapshot here before entering Design.")
        return
    st.info(f"Pinned UTC: {snapshot.at_utc} · snapshot identity {snapshot.snapshot_sha256[:14]} · "
            "source: inline/local providers")
    temp = dict(snapshot.temperature_profile_C)
    salt = dict(snapshot.salinity_profile_psu)
    depths = sorted(set(temp) | set(salt))
    st.dataframe([{"Depth [m]": d,
                   "T in-situ [°C]": float(np.interp(d, *zip(*snapshot.temperature_profile_C))),
                   "SP [Practical Salinity]": float(np.interp(d, *zip(*snapshot.salinity_profile_psu)))}
                  for d in depths], use_container_width=True, hide_index=True)
    st.caption(f"Uniform current: east {snapshot.current_east_north_mps[0]:+.3f} m/s, "
               f"north {snapshot.current_east_north_mps[1]:+.3f} m/s. "
               "Profile values are converted to TEOS-10 only inside the headless evaluator.")
    with st.expander("Exact provider provenance"):
        st.json(snapshot.providers)


def _numeric(name: str, value: float, *, lo: float, hi: float,
             step: float, fmt: str = "%.2f") -> float:
    return float(st.number_input(name, min_value=lo, max_value=hi, value=float(value),
                                 step=step, format=fmt,
                                 key="design_control_" + name))


def _saved_or_pinned_scalar(source: dict, snapshot, key: str, default: float) -> float:
    """Reopen from locked design values; nonconstant providers use the pin."""
    spec = source.get(key)
    if spec is not None and spec["provider"] == "constant":
        return float(spec["value"])
    return float(snapshot.source_scalars.get(key, default))


def _design(project, store: ProjectStore):
    snapshot = st.session_state.get("snapshot")
    if snapshot is None:
        st.warning("First pin a water-column snapshot in Ocean; Design never fetches environmental data.")
        return
    cfg = project.config.normalized
    st.subheader("Design · live single-port near-field")
    st.caption("Geometry is local ENU: depth positive downward; azimuth clockwise from north; "
               "vertical angle positive upward. Only one round submerged port is supported.")
    left, right = st.columns([1.0, 2.2], gap="large")
    with left:
        geom = cfg["outfall"]
        depth = _numeric("Discharge depth [m]", geom["discharge_depth_below_surface_m"],
                         lo=0.0, hi=cfg["site"]["water_depth_m"], step=0.5)
        diam = _numeric("Port diameter [m]", geom["diameter_m"], lo=0.01, hi=25.0, step=0.05)
        angle = _numeric("Vertical angle [°]", geom["vertical_angle_deg"],
                         lo=-90.0, hi=90.0, step=5.0, fmt="%.0f")
        az = _numeric("Azimuth [° true N]", geom["azimuth_deg"],
                      lo=0.0, hi=359.9, step=5.0, fmt="%.1f")
        source = cfg["forcing"]["source"]
        flow = _numeric("Flow [m³/h]", _saved_or_pinned_scalar(source, snapshot, "flow_m3h", 0.0),
                        lo=0.01, hi=1_000_000.0, step=50.0)
        default_kind = "Process ΔT" if "delta_T_C" in source else "Absolute outlet T"
        temp_mode = st.radio("Outlet temperature definition", ["Process ΔT", "Absolute outlet T"],
                             index=0 if default_kind == "Process ΔT" else 1,
                             key="design_control_temperature_mode", horizontal=True)
        ambient_t = float(np.interp(depth, *zip(*snapshot.temperature_profile_C)))
        if temp_mode == "Process ΔT":
            delta = _numeric("Process ΔT [°C]", _saved_or_pinned_scalar(source, snapshot, "delta_T_C", 10.0),
                             lo=0.01, hi=60.0, step=0.5)
            absolute = None
        else:
            absolute = _numeric("Absolute discharge T [°C]",
                                _saved_or_pinned_scalar(source, snapshot, "discharge_temperature_C", ambient_t + 10.0),
                                lo=-2.0, hi=100.0, step=0.5)
            delta = None
        st.caption(f"Local ambient T at outlet: {ambient_t:.2f} °C")
    try:
        candidate = candidate_config(cfg, depth_m=depth, diameter_m=diam,
                                     angle_deg=angle, azimuth_deg=az, flow_m3h=flow,
                                     discharge_temperature_C=absolute, delta_T_C=delta)
        import hashlib, json
        candidate_key = hashlib.sha256(json.dumps(candidate, sort_keys=True,
                                                separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        key = (snapshot.snapshot_sha256, candidate_key)
        cache = st.session_state.setdefault("evaluations", {})
        if key not in cache:
            began = time.perf_counter()
            with st.spinner("Evaluating near-field model and reconstructed field…"):
                cache[key] = (evaluate_design(candidate, snapshot), time.perf_counter() - began)
            if len(cache) > 12:
                cache.pop(next(iter(cache)))
        evaluation, elapsed = cache[key]
    except (PlumeError, RuntimeError, ValueError) as exc:
        with right:
            st.error(f"No current result: {exc}")
        return
    m = evaluation.metrics
    locked_snapshot = store.load_locked_snapshot(project) if project.is_locked else None
    is_saved = bool(project.locked_revision_id and project.locked_config_sha256 and
                    locked_snapshot is not None and
                    locked_snapshot.snapshot_sha256 == snapshot.snapshot_sha256 and
                    candidate_key == _candidate_lock_fingerprint(project.config.normalized))
    with right:
        st.caption(("LOCKED DESIGN" if is_saved else "UNSAVED CANDIDATE") +
                   f"  ·  MODEL/FIELD UNVALIDATED  ·  calculate {elapsed:.2f}s (cached by candidate)")
        k1, k2, k3 = st.columns(3)
        k1.metric("Section peak ΔT", f"{m['section_peak_delta_T_C']:.2f} °C")
        k2.metric("Plan peak ΔT", f"{m['plan_peak_delta_T_C']:.2f} °C")
        length = m["plan_threshold_farthest_radius_m"]
        k3.metric(f"ΔT {m['threshold_delta_T_C']:g}°C plan radius",
                  "not sampled" if length is None else f"{length:.1f} m")
        fig = render_field_pair(
            evaluation.section, evaluation.plan,
            threshold_delta_T_C=m["threshold_delta_T_C"],
            title=f"{project.config.normalized['project']['name']} / pinned {snapshot.at_utc}")
        st.pyplot(fig, use_container_width=True)
        import matplotlib.pyplot as plt
        plt.close(fig)
        st.caption("Cyan is model-derived configured ΔT contour; heat colours are local in-situ excess. "
                   "Background is absolute ambient temperature. Plan is a single horizontal depth slice, "
                   "not a column maximum. No prediction beyond the near-field support.")
        if m["grid_boundary_threshold_contact"]:
            st.warning("Threshold reaches a plotted grid boundary: sampled extent may be clipped.")
        st.caption(f"Termination: {m['termination_reason']} · final bulk dilution "
                   f"{m['final_bulk_dilution']:.2f} · plan depth {m['plan_slice_depth_m']:.1f} m")
        st.warning("UNVALIDATED — MODEL-CLOSURE-1 and FIELD-PROFILE-1 remain open. "
                   "Slice extents are provisional design indicators, NOT permit pass/fail metrics.")
    a, b = st.columns([1, 1])
    with a:
        if st.button("Add to comparison", use_container_width=True):
            items = st.session_state.setdefault("comparisons", [])
            items.append({"Candidate": candidate_key[:10], "Depth [m]": depth,
                          "Diameter [m]": diam, "Flow [m³/h]": flow,
                          "Azimuth [°]": az, "Angle [°]": angle,
                          "Section ΔT peak [°C]": m["section_peak_delta_T_C"],
                          "Plan radius ΔT limit [m]": m["plan_threshold_farthest_radius_m"],
                          "Bulk dilution": m["final_bulk_dilution"]})
    with b:
        if st.button("Save & lock design revision", type="primary", use_container_width=True):
            try:
                updated = store.save_revision(project, evaluation)
                st.session_state["next_project"] = updated.project_id
                st.success(f"Locked revision {updated.locked_revision_id}")
                st.rerun()
            except PlumeError as exc:
                st.error(str(exc))
    if st.session_state.get("comparisons"):
        st.subheader("Compared candidates (one pinned ocean state)")
        st.dataframe(st.session_state["comparisons"], use_container_width=True, hide_index=True)
    if project.is_locked:
        with st.expander("Export selected locked config"):
            try:
                portable = export_portable_yaml(project)
                st.download_button("Download provider-based locked YAML", portable,
                                   file_name=f"{project.project_id}.yaml", mime="text/yaml")
            except PlumeError as exc:
                st.caption(str(exc))
            st.download_button("Download self-contained locked snapshot YAML",
                               export_snapshot_yaml(project, locked_snapshot),
                               file_name=f"{project.project_id}_snapshot.yaml", mime="text/yaml")
            st.caption("Snapshot YAML represents one pinned hour; it is NOT an annual forcing history. "
                       "No machine-local cache paths or credentials are embedded.")


def _candidate_lock_fingerprint(cfg: dict) -> str:
    import hashlib, json
    return hashlib.sha256(json.dumps(cfg, sort_keys=True,
                                     separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def main() -> None:
    st.sidebar.title("PLUME  /  DESIGN STUDIO")
    store = ProjectStore(_workspace())
    ids = store.list_projects()
    if "next_project" in st.session_state:
        st.session_state["selected_project"] = st.session_state.pop("next_project")
    if st.session_state.get("selected_project", "New project") not in ("New project", *ids):
        st.session_state["selected_project"] = "New project"
    selected = st.sidebar.selectbox("Workspace projects", ["New project", *ids],
                                    key="selected_project")
    st.sidebar.caption("Local workspace only · no Copernicus credentials required")
    st.title("Plume · Thermal discharge twin")
    st.caption("Design candidate / source physics: reference-formulated, not physically validated")
    stages = ["Project", "Ocean", "Design", "Simulate", "Results"]
    stage = st.radio("Workflow", stages, horizontal=True, label_visibility="collapsed")
    if selected == "New project":
        _new_project(store)
        return
    _reset_project(selected, store.root)
    try:
        project = store.open(selected)
    except PlumeError as exc:
        st.error(str(exc))
        return
    if st.session_state.get("snapshot") is None and project.is_locked:
        try:
            st.session_state["snapshot"] = store.load_locked_snapshot(project)
        except PlumeError as exc:
            st.error(str(exc))
    if stage == "Project":
        st.subheader(project.config.normalized["project"]["name"])
        st.write(f"Project ID: `{selected}` · WGS84 "
                 f"{project.config.normalized['site']['latitude_deg']:.5f}°, "
                 f"{project.config.normalized['site']['longitude_deg']:.5f}° · "
                 f"water depth {project.config.normalized['site']['water_depth_m']:.1f} m")
        st.write("Locked revision:", project.locked_revision_id or "none; new project")
        st.caption("Saved revisions and projects remain in the configured ignored workspace. "
                   "Historical runs are not produced in DESIGN-1.")
    elif stage == "Ocean":
        _ocean(project)
    elif stage == "Design":
        _design(project, store)
    elif stage == "Simulate":
        st.info("TIME-1 will implement historical replay against the locked config and "
                "reuse cached ocean forcing. DESIGN-1 does not invent annual results.")
    else:
        st.info("PERMIT-1 will implement annual criteria, receptor compliance statistics "
                "and animation. DESIGN-1 only provides unvalidated snapshot design indicators.")


if __name__ == "__main__":
    main()
