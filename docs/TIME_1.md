# TIME-1 source candidate — Ocean history, Copernicus and bounded replay

**Branch:** `time-1a-historical-foundation`, draft PR #11. TIME-1A/1B/1C are sequential source slices intended for one laptop closer. Source completion is NOT integration, physical validation, an actual Copernicus service success, or permission to merge.

## What is implemented

- TIME-1A: normalized, time/depth-indexed UTC scalar/vector forcing, raw-file SHA cache, explicit gaps, original plant-source preservation, one selected normalized `PinnedSnapshot` with ENU current shear.
- TIME-1B: headless `copernicus` provider backed by optional `copernicusmarine.open_dataset`; bounded rectilinear wet-cell selection, requested vs actual location and depth provenance; correct variable quantity metadata, surface boundary proxy warnings, no bottom extrapolation; the Ocean stage allows map-assisted **new project** coordinates, explicit acquisition of history, environmental heatmaps and pinning a timestamp.
- TIME-1C: `plume.runner` reconstructs original time-varying source providers from the **locked DESIGN-1 pinned revision**, validates the exact history SHA and fixed geometry, then explicitly executes bounded quasi-steady MODEL-1/FIELD-1 solves, saves one row per UTC slot (including MISSING), source/revision/model/output digests, selected fields, and exploratory near-field metrics. Streamlit Simulate/Results views use this same headless code.

**Not delivered by TIME-1:** physically calibrated near-field entrainment (`MODEL-CLOSURE-1`), independent field-profile qualification (`FIELD-PROFILE-1`), the frozen physical tolerance gate (`MODEL-TOL-1`), qualified far field, legally interpreted permit criteria/exceedance statistics (`PERMIT-1`), probe/SCADA realtime feeds or guaranteed Copernicus coverage at every coastal site. Annual speed and uninterrupted 8,760-solve workload remain unmeasured.

## Local deterministic laptop smoke (no Copernicus account)

Use VS Code's Git panel to pull the specific draft branch. On Windows from the Plume repo root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[studio,ocean]" pytest
.\.venv\Scripts\python.exe -m compileall -q src apps tools tests
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe tools/generate_time1_demo.py --output workspace/time1_demo
.\.venv\Scripts\python.exe -m streamlit run apps/design_studio.py
```

The generator writes **only** to a new directory under ignored `workspace/`; it refuses to overwrite data or create inputs under `References/`. Select `workspace/time1_demo/history_demo.yaml` as the Source config when creating a new project. Recommended walkthrough:

1. Use the New Project map click (or exact WGS84 numbers) and create a unique project ID (e.g. `time1_check`). Site depth 25 m for the demo; if you move outside the demo location, this is a synthetic engineering test, not representative measurements.
2. Ocean → **Load ocean history**. Expect 72 hourly slots, 71 complete, one deliberate missing T profile at 2025-01-02 13:00 UTC. Inspect the visibly gapped temperature history, current, SP, and exact provenance.
3. Pin an available hour, then Design → change diameter/angle/flow and confirm real computed section/plan from unchanged snapshot, adjust the cyan preview line, lock a revision. After locking, the operating point is fixed for design, but the history must recover the original CSV plant flow/ΔT descriptors.
4. Ocean history should still be valid; Simulate → run first **3 slots** only (fast mechanical smoke, does not include the intentionally missing hour). Confirm three model rows, no provider refetch, correct original varying plant inputs and a `COMPLETED` manifest. Results → compare metrics/time series; every value is **UNVALIDATED, NOT_ASSESSED**. A longer explicit run includes gaps as `MISSING`, never fabricated.
5. Capture `pytest` counts and any warnings, the exact local git head (from VS UI if command-line Git is unavailable), one Ocean screenshot, and one Results screenshot. Don't use the reference files for raw-byte experiments on an older CRLF-converted Windows checkout.

You may omit the `ocean` dependency if testing ONLY synthetic CSV history (and then skip optional Copernicus adapter tests), but the preferred complete closer installs both extras and reports any skips explicitly.

## Copernicus Marine source descriptor — split datasets

This is *illustrative*, **not** a verified working dataset ID. Check dataset IDs, availability and variable units against the current Copernicus catalogue; `dataset_id` is not credential state.

```yaml
forcing:
  clock: {start: '2025-07-01T00:00:00Z', end: '2025-07-04T00:00:00Z', step: 'P1D'}
  source:
    flow_m3h: {provider: constant, value: 540}
    delta_T_C: {provider: constant, value: 10}
  ambient:
    temperature_profile_C:
      provider: copernicus
      role: temperature
      dataset_id: REPLACE_WITH_VERIFIED_THETAO_DATASET_ID
      variable: thetao
      temperature_kind: potential_pt0
      salinity_kind: practical
      # salinity_variable: so  # ONLY if the SAME dataset contains co-located so
    salinity_profile_psu:
      provider: copernicus
      role: salinity
      dataset_id: REPLACE_WITH_VERIFIED_SO_DATASET_ID
      variable: so
      salinity_kind: practical
    current_profile:
      provider: copernicus
      role: current
      dataset_id: REPLACE_WITH_VERIFIED_UO_VO_DATASET_ID
      u_variable: uo
      v_variable: vo
```

A `potential_pt0` temperature provider without `salinity_variable` emits **raw potential-temperature history**. The Ocean diagnostic says so; when selecting a single UTC hour, history pairs it with that hour's normalized Practical Salinity depth profile and converts to in-situ ITS-90 using GSW (`SA_from_SP`, `CT_from_pt`, `t_from_CT`) at the selected cell pressure. The `PinnedSnapshot` includes the explicit conversion provenance. When `salinity_variable: so` is supplied, **that same Copernicus dataset must contain so**; the provider can normalize its own co-located T/SP pair. No silent conversion of potential/conservative/in-situ quantities is permitted.

### Wet-cell and vertical coverage policy

The provider requests a small geographic box around the WGS84 site; checks nearest viable **wet** rectilinear cell(s), bounded by explicit `max_fallback_km` (default 8 km), and retains *requested and actual* coordinates, depth levels, source version/variable metadata and warnings. Native levels must span full depth **to/under** the configured seabed; the bottom is interpolated only within measured/model depths and is never extrapolated below the deepest wet level. A near-surface first native layer up to `surface_proxy_limit_m` (default 1.1 m) may be held explicitly to represent 0 m; this is flagged as a **proxy, not a 0 m observation**. Deeper surface or insufficient seabed coverage fails. Missing/masked hours remain gaps. A downloaded coastal cell may be wet to the requested seabed but masked in irrelevant deeper downloaded layers: only the levels needed to bracket that seabed participate in the wet-cell check; the downloaded depth grid is still recorded. An in-situ config must match native in-situ temperature metadata and cannot override native potential temperature; wrong role-specific options are rejected rather than silently ignored. If separately acquired Copernicus ambient variables' actual wet cells differ by more than 2 km, acquisition refuses to merge them into a fictitious single water column; smaller differences stay in the provenance. This is an **engineering software policy, not a physical validation**.

Dataset cadence must match the requested exact whole-second UTC clock. No automatic temporal resampling from daily products into hourly source data. Product-specific metadata, ocean grid resolution, near-coast masked cells, dataset expiry/service drift and live login have **not yet been independently exercised**. For more detail see the Copernicus Marine [open_dataset official API documentation](https://help.marine.copernicus.eu/en/articles/8287609-copernicus-marine-toolbox-api-open-a-dataset-or-read-a-dataframe-remotely).

### Optional live Copernicus closer (separate from deterministic smoke)

If the user has an ordinary Copernicus Marine account/working service, configure it via **ignored local environment variables**, never YAML, Git or chat, verify a small known-wet open-water 1–3 day request and compare native variable metadata, site-depth feasibility, GSW normalization and requested/actual coordinates. Nearshore fjord coverage is not guaranteed; if the selected dataset masks the fjord, **record coverage HOLD**, do not hallucinate a wet cell. All acquired data stay in the ignored workspace provider cache; `refresh=True` explicitly refreshes remote inputs when products update.

## Output / identity contract

`plume.runner.restored_forcing_config(project, store)` recovers original time-varying plant providers from the saved locked snapshot. `preflight_history()` binds exact history request/data SHA, project revision, selected site/ambient, source-provider identity and missing slots; refuses stale configuration. `run_history()` writes a new workspace-local `runs/time1-<id>` with manifest/config, one `MISSING` or `SOLVED` record per selected timestamp, immutable output SHA-256 checks, provisional max/P95/P99 for **sampled-slice metrics only**, and optionally one computed near-field field image. Failures leave `stage: FAILED` and cannot be loaded as completed results. Old runs stay intact when the locked project changes; Results marks them stale.

**Semantics:** `complete_historical_period` only means all requested clock slots had forcing and were simulated (a software coverage property), **not** physical model validity, permit compliance, or verified hydrodynamics. True configured criteria pass/fail, exceedance days/hours and annual legal Results are owned by later PERMIT-1.

### What this source slice does not yet expose

The current Ocean picker follows the historical period in the saved config; an automatic previous-calendar-year **editable period control** is not yet offered in Streamlit. The optional map proposes coordinates at **new project creation**; a locked project's site cannot be moved without creating a new design revision. Copernicus access remains optional and may be limited by coastal wet-cell availability, with no accepted external validation of the requested product IDs. A complete year may require 8,760 real model solves, not a synthetic annual shortcut.

## Retirement evidence and ownership

This is one **draft source candidate**, not approved integration. Await one exact-head full-checkout run with official GSW + optional ocean/Studio dependencies, review the synthetic 3-step local workflow, separately test one genuine Copernicus service request if possible, and record all limitations. No Actions without fresh explicit human approval for that run. All files in `References/` immutable. No main merge without explicit human authorisation.
