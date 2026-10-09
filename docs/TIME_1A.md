# TIME-1A — Headless historical forcing and local provider cache

**State:** source candidate on `time-1a-historical-foundation`, not an annual permit assessment. Requires separate exact-head integration testing, review and explicit human merge authorisation.

## Why this seam exists

DESIGN-1 pins one temperature/salinity/current water column and a plant operating point. TIME-1A adds a **reusable ocean/plant history contract** without changing the plume physics or introducing UI-specific historical data parsing. The selected hour becomes an ordinary, SHA-pinned DESIGN-1 `PinnedSnapshot`; a future runner may feed those snapshots to `evaluate_design` or a headless timestep engine.

Do **not** pass a DESIGN-1 **locked constant operating point** as the complete historical plant source. Historical `flow_m3h` and `delta_T_C` or `discharge_temperature_C` providers remain the original time-dependent descriptors throughout selection and cache provenance. A candidate that replaces one with a constant is rejected for history sampling.

## CSV provider contracts

`csv_time_depth_profile` returns `time_depth_profile`; its CSV columns are `time,depth_m,value`. It may serve `forcing.ambient.temperature_profile_C` (in-situ ITS-90 °C, **not Copernicus potential temperature**) or `salinity_profile_psu` (Practical Salinity). Example:

```yaml
temperature_profile_C:
  provider: csv_time_depth_profile
  path: water_temperature.csv
  time_column: time
  depth_column: depth_m
  value_column: value
```

`csv_time_vector_profile` returns `time_depth_vector`; columns `time,depth_m,u_east_mps,v_north_mps`, where u and v use local **ENU** east and north velocity components in m/s. Neither bearing nor speed/magnitude alone is silently interpreted as ENU components.

```yaml
current_profile:
  provider: csv_time_vector_profile
  path: east_north_currents.csv
```

`time_column`, `depth_column`, and applicable scalar/vector column names are configurable. File paths are interpreted relative to the source config directory. Raw file SHA-256 and normalized descriptor, resolved input path, exact request, provider version/kind, selected time and water-column depths are preserved in the provenance chain.

**Validation:** every row must use a timezone-aware UTC-convertible ISO timestamp, a nonnegative finite depth and finite values. Timestamp groups must increase strictly, and within each group depths must increase strictly (no duplicates). TIME-1A intentionally uses **whole-second sampling**; subsecond time rows or subsecond forcing clock steps must fail rather than be rounded or aliased. A selected profile must explicitly cover surface depth 0 and the configured seabed depth and contain at least two levels. No extrapolation, guessed depths or implicit interpolation across missing times. Temperatures are in-situ ITS-90; salinity Practical Salinity. Thermodynamic conversion to TEOS-10 remains in the MODEL boundary.

Existing `constant`, `csv` scalar-time-series, `inline_profile`, `csv_depth_profile`, and `constant_vector` providers remain supported. A new provider shape is registered through the shared normalized-provider registry, not attached to Streamlit.

## Headless API

```python
from plume.config import load_config
from plume.history import acquire_history

config = load_config("my_historical_project.yaml")
history = acquire_history(config)  # explicit acquisition, local workspace cache
print(len(history.clock_times), len(history.available_times))
print(history.missing_by_time)      # never silently interpolated
selected = history.snapshot_at(config, "2025-07-15T12:00:00Z")
# selected is the same PinnedSnapshot contract accepted by evaluate_design.
for pinned in history.iter_available(config):
    # future time runner; no solver, permitting verdict or surface claim here
    pass
```

`forcing.clock` produces a UTC grid from `start` **inclusive** to `end` **exclusive**, stepped at whole seconds. A selected timestamp must be exactly on-grid and have every requested mandatory ambient and plant source; otherwise selection fails with explicit missing keys. `available_times` lists complete slots. `missing_by_time` lists incomplete slots and their missing provider names. `iter_available` yields deterministic pinned inputs with no provider calls. The current profile is additionally serialized as `current_profile_east_north_mps` (depth,u,v triples) when required; legacy constant-current snapshots omit this optional field and preserve their original SHA identity. MODEL-1 interpolates u/v at depth grid points; it does not silently flatten a vertically sheared current.

## Cache and invalidation

Cache JSON belongs only under the configured gitignored workspace:

- shared: `workspace/_cache/providers/history/<request-sha256>.json`
- private: `workspace/projects/<project-id>/_cache/history/<request-sha256>.json`

The deterministic request SHA includes site coordinates/water depth, entire forcing clock and normalized source/ambient provider descriptors, plus **raw bytes SHA-256** of any local CSVs and resolved paths. It intentionally excludes outfall geometry/plot threshold. Edited local files generate a new key and reacquisition; repeated `acquire_history` for unchanged local inputs reuses the validated disk cache, and later `snapshot_at` never refetches or reopens providers. The data SHA also pins normalized records, gaps and provenance; a corrupt cache is rejected loudly rather than silently trusted. Explicit `refresh=True` permits reloading the same request.

Note: local CSV bytes are re-hashed at **acquisition** to prevent stale cache hits; they are not reread on design selection. For future remote Copernicus providers, explicit dataset, actual wet-cell, version, temporal/spatial/depth selection and remote freshness policy will be required; this release does **not** implement that adapter or credentials.

## Separate responsibilities, gates and limitations

- **TIME-1A:** normalized historical CSV contracts, exact-time gap-aware selection, cache identity and model-compatible pinned inputs; no Ocean UI or time-runner results.
- **TIME-1B:** Copernicus/native units (potential temperature vs in-situ T), wet-cell fallback, map/timeseries Ocean UI, explicit account/cache metadata.
- **TIME-1C:** bounded quasi-steady historical runner, run manifest and honest step metrics; simulation metrics are distinct from later PERMIT-1 regulatory assessment.
- **PERMIT-1:** configured permit criteria, exceedance aggregation, Results and animation.

Physical `MODEL-CLOSURE-1` and `FIELD-PROFILE-1` remain open and `MODEL-TOL-1` blocked. All generated caches and synthetic charts live outside the Git tree. No material under `References/` is touched. The synthetic plot generated for this source sprint is an **input-data diagnostic**, not a physical validation or real Copernicus measurement.
