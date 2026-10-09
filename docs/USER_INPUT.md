# User input — durable accepted direction

This file records accepted project direction that should survive chat/session boundaries. It is not a transcript.

## 2026-10-07 bootstrap

- `fellesinnov/Plume` is independent from BOOSTED, but should reuse only workflow concepts that proved useful.
- Keep the process simple and sandbox-first.
- GitHub Actions is manual opt-in because credits are scarce.
- Maintain durable owners for live work/evidence.
- Prototype files do not create backward-compatibility obligations.

## 2026-10-07 SPEC-0 product direction

- Plume's primary target is a **thermal-plume digital twin** for customer permit-support work, not merely a one-case screening calculator.
- Customer-facing scope is thermal: excess/absolute temperature and the spatial/temporal plume relevant to permit limits.
- Fixed configuration includes site/outfall geometry such as location, depth of discharge, diameter, angle/azimuth and later multiport details.
- Outlet architecture must remain open to multiple geometries. First implementation can be a single round submerged port; future candidates may include multiport diffusers, vertical/horizontal jets, near-surface/surface discharge and other outlet adapters where the physics/reference evidence supports them.
- Time-varying forcing can include flow, discharge temperature/process ΔT, ambient water-temperature layers, salinity/density layers and current.
- Historical replay should support Copernicus Marine; later live probes/ADCP/SCADA should plug into the same provider contracts.
- Expected outputs include permit-oriented time series, worst cases, threshold plume size/extent, surface hotspot metrics, section/plan plots and animations through a year.
- Near-field physics is core. A qualified simple/prescribed-current far field may be added separately. Plume should not attempt to replace full coastal hydrodynamic/CFD models for bathymetric steering, shoreline circulation or recirculation.
- Add an explicit **Design Mode** before annual simulation: load one representative/worst water column and one source operating state, then rapidly vary outlet depth, diameter, angle, azimuth, port count/spacing where supported, flow and discharge temperature; compare permit metrics/plots and save the selected geometry as a normal project config.
- The design workflow should remain useful even before Copernicus is connected: a profile can come from inline/file/manual data. Later it can select a worst/representative historical timestamp from a provider cache.
- Configs must be flexible/versioned and may choose what artifacts to retain.
- Runtime provider data, caches, plots, fields, animations and reports should default to a configurable **gitignored workspace** so quick engineering work does not pollute source history.
- Core engine/provider/result contracts should remain UI-independent so a future light HeatHandler integration is straightforward.
- Digital-twin operation may later use simple field measurements/probes to compare/calibrate the model and monitor permit-relevant quantities such as surface temperature. Calibration evidence must remain distinct from independent verification.
- Copernicus credentials must not be committed. A throwaway account may later be supplied to the ChatGPT sandbox through an ignored/local mechanism.
- All third-party/reference distributions belong under `References/` and are immutable during normal work.
- PLUMES2.0 is **not** privileged as physical truth. Accuracy matters more than parity with any one implementation. Use multiple independent references, literature and measurements to triangulate model behaviour.
- GPL-3.0 reference software may be run freely as an external oracle/reference for this consulting/internal-service use case. Direct incorporation/adaptation into the Plume product remains a deliberate license/deployment decision so future customer installation remains flexible.
- The pre-SPEC-0 prototype should be preserved in Git history/archive branch but removed from the active product tree so its experimental calibration does not become inherited model truth.
- ChatGPT is the routine repository owner/writer for normal source/docs/branch/PR maintenance. The human will generally avoid direct repository edits except deliberate user-input/gate decisions. Existing explicit human merge authority remains unchanged unless separately revised.

## 2026-10-07 Design Studio refinement

- Preferred first UI is a Streamlit-style **Plume Design Studio** analogous in usability to the HeatHandler configurator while keeping core code independent of Streamlit.
- Main user flow: **Project → Ocean → Design → Simulate → Results**.
- A named project stores location/site, criteria, selected design/config revision and run history in the gitignored workspace.
- Ocean view selects a location, fetches/caches a historical environmental period (default previous complete calendar year when available), plots environmental history, and lets the user pick a date/time whose full T/S/current profile becomes the pinned Design Mode snapshot.
- Live Design controls rerun plume calculations against the pinned snapshot without refetching Copernicus.
- The primary section plot follows the supplied mockup: real ambient layers/profiles plus model-derived excess-temperature ΔT contours, physical depth/distance axes and explicit permit isotherms.
- Saving creates a project/config revision; simulation uses the selected locked revision. Later edits mark old results stale for the new revision but preserve them.
- Provider cache, model-result cache and render cache should invalidate independently so changing geometry does not redownload ocean data and changing plot appearance does not rerun physics.
- Annual runs should not be forced to store dense spatial fields for every timestep; compact metrics/model state plus selected/cadenced fields should support fast rerendering and animation.

## 2026-10-09 DESIGN-1 laptop feedback

- User demonstrated a real Windows Streamlit session: Project creation, local Ocean pin, live computed section/plan rerenders, variant comparison, saving and exporting. The plot's cyan +2 °C excess-temperature isotherm was positively received.
- Requested an adjustable line/tolerance, initially defaulting to +2 °C. Implement first as an explicitly labelled **visualisation-only preview**: changing the level set must reuse the same solved field and keep the saved config's criteria intact. A future criterion-editing workflow needs an explicit design/permit decision, not an implicit on-screen display change.
- Reported Windows `pytest` 77 passed / 1 failed due to immutable reference worktree byte-size mismatch; protect checked-in reference bytes using Git checkout attributes, not by modifying any `References/` content or relaxing the exact manifest locks.

## 2026-10-09 TIME-1A authorisation

- User explicitly authorised `GO TIME-1A!` for a cloud-only first historical ocean foundation while traveling. Prior accepted scope: timestamped temperature/salinity/current contracts, reusable normalized provider cache, deterministic selection/replay inputs, no refetch on outlet geometry edits, and illustrative strictly synthetic diagnostic plot. No approval for Actions or `main` merge; Copernicus service integration and Ocean UI belong to later TIME-1B.

## 2026-10-09 TIME source completion request

- User asked to **finish TIME source development in the cloud** and reserve one laptop session for the mechanical/runtime closer. Accepted scope: TIME-1A + optional real Copernicus-native Ocean/Map + bounded locked historical replay/Results, with the first demo working entirely from deterministic synthetic CSV data and no credentials. No user authorisation for GitHub Actions, physical-calibration claims or merging PR #11 into `main`.
