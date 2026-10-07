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
- Fixed configuration includes site/outfall geometry such as location, depth of discharge, diameter, angle and later multiport details.
- Time-varying forcing can include flow, discharge temperature/process ΔT, ambient water-temperature layers, salinity/density layers and current.
- Historical replay should support Copernicus Marine; later live probes/ADCP/SCADA should plug into the same provider contracts.
- Expected outputs include permit-oriented time series, worst cases, threshold plume size/extent, surface hotspot metrics, section/plan plots and animations through a year.
- Near-field physics is core. A qualified simple/prescribed-current far field may be added separately. Plume should not attempt to replace full coastal hydrodynamic/CFD models for bathymetric steering, shoreline circulation or recirculation.
- Configs must be flexible/versioned and may choose what artifacts to retain.
- Runtime provider data, caches, plots, fields, animations and reports should default to a configurable **gitignored workspace** so quick engineering work does not pollute source history.
- Core engine/provider/result contracts should remain UI-independent so a future light HeatHandler integration is straightforward.
- Copernicus credentials must not be committed. A throwaway account may later be supplied to the ChatGPT sandbox through an ignored/local mechanism.
- All third-party/reference distributions belong under `References/` and are immutable during normal work.
- The pre-SPEC-0 prototype should be preserved in Git history/archive branch but removed from the active product tree so its experimental calibration does not become inherited model truth.
