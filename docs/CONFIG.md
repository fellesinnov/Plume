# Configuration, providers and workspace

**Status:** SPEC-0 contract with REF-1 coordinate/thermodynamic conventions. CORE-0 implements the schema-v1 headless loader/normalizer, structural outlet-adapter registry, deterministic local providers and prepared-run manifest/workspace skeleton. The MODEL-1 candidate adds the single-round-port near-field kernel and a GSW-backed TEOS-10 model-state boundary, but the physical current-entrainment closure remains gated by `MODEL-CLOSURE-1`; no Copernicus adapter or provider-side TEOS-10 conversion is implied yet.

## 1. Principles

- Config is the durable description of a Plume project/run.
- UI state must be serializable into the same schema.
- YAML and JSON may both be accepted; the normalized schema is authoritative.
- SI is the default.
- Secrets never appear in config.
- Paths are relative to the config file unless explicitly absolute. Because `configs/example.yaml` lives under `configs/`, it uses `../workspace` to resolve to the repository-level default `workspace/`.
- Downloaded/provider data and generated outputs are local artifacts, not source.
- Provider-specific data is normalized before it reaches the model.
- Outlet geometry is type-tagged and extensible; unsupported geometry must fail explicitly rather than silently falling back.

See [../configs/example.yaml](../configs/example.yaml).

## 2. Top-level schema

The first schema should keep these stable concepts:

```text
schema_version
project
site
outfall
forcing
model
criteria
workspace
outputs
```

Provider/file and outlet-type details may evolve behind those concepts.

## 3. Outfall contract

All configs contain a type-tagged `outfall` object.

Common concepts:

```text
type
discharge position / depth
vertical angle
azimuth / orientation
```

Type-specific geometry is explicit.

Initial type:

```yaml
outfall:
  type: single_round_port
  diameter_m: 0.8
  discharge_depth_below_surface_m: 12.0
  vertical_angle_deg: 0.0
  azimuth_deg: 90.0
```

Future types may include multiport diffusers and surface/near-surface outlets. Their schema can add port count, spacing/layout or other geometry without changing provider/time-runner contracts.

Representation in config does not mean a physics implementation exists. CORE-0 rejects outlet types without a registered structural adapter. Once model selection is introduced, the runner/model boundary must additionally reject a structurally representable outlet when no selected qualified physics adapter implements it.

### Coordinate and angle convention

The normalized product/model convention is local **ENU**, independent of PLUMES/Visual Plumes
legacy axes:

- `+x = east`;
- `+y = north`;
- `+z = up`;
- local free surface `z = 0` for a design/simulation snapshot;
- depth values are separately stored positive downward;
- `azimuth_deg` is clockwise from true north: 0° north, 90° east;
- `vertical_angle_deg` is measured from horizontal, positive upward;
- ambient vectors use `u_east_mps` and `v_north_mps`.

Reference adapters own any conversion required to compare against a PLUMES/SFEI local-axis
convention. A reference convention must never silently become the product convention.

## 4. Forcing references

A forcing value is described by a small source descriptor rather than a hard-coded API call.

Examples:

```yaml
flow_m3h:
  provider: constant
  value: 4000.0
```

```yaml
flow_m3h:
  provider: csv
  path: plant/flow.csv
  time_column: timestamp
  value_column: flow_m3h
```

CORE-0's schema-v1 `csv` implementation is deliberately limited to a scalar time series (`time`, `value`) with timezone-aware, strictly increasing timestamps. DESIGN-1 adds `csv_depth_profile` for static temperature/salinity depth columns (`path`, `depth_column`, `value_column`), which is hashed/provenance tracked, requires finite increasing depth and retains its original files. Pinned snapshots require explicit full-water-column surface and seabed levels. Depth-profile and vector CSV shapes can extend the same provider interface when a concrete use case requires them.

A profile:

```yaml
temperature_profile_C:
  provider: inline_profile
  levels:
    - {depth_m: 0, value: 10.2}
    - {depth_m: 20, value: 7.4}
```

Copernicus:

```yaml
temperature_profile_C:
  provider: copernicus
  dataset_id: cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m
  variable: thetao
  selection: full_water_column
```

Credentials are resolved from environment variables, for example:

```text
COPERNICUSMARINE_SERVICE_USERNAME
COPERNICUSMARINE_SERVICE_PASSWORD
```

The config may name credential *environment variable names* later, but never store credential values.

## 5. Normalized provider contracts

CORE-0 normalizes provider **shape and provenance**, not seawater thermodynamics. Inline/manual temperature and salinity values retain the explicit quantity meaning carried by their forcing key/config contract. The MODEL-1 candidate defines the model-facing TEOS-10 state as Absolute Salinity plus Conservative Temperature and provides the pressure-aware GSW density/output-temperature boundary; provider/user quantities still must be converted deliberately before entering that state.

Provider adapters should return a small number of model-facing shapes.

### Scalar time series

```text
time, value
```

Examples: flow, process ΔT, absolute discharge temperature.

### Scalar depth profile at one time

```text
depth_m, value
```

Examples: temperature, salinity.

### Time-varying depth profile

```text
time, depth_m, value
```

### Time-varying vector profile

```text
time, depth_m, u_east_mps, v_north_mps
```

### Bathymetry

Raster/grid or normalized point cloud with explicit coordinate reference/datum.

Every provider response must also return provenance/warnings separately from the numerical array.

### Thermodynamic normalization

The user/provider-facing schema may accept familiar temperature and practical-salinity values, but
the near-field physics contract should not treat an ambiguous `temperature_C` or `salinity`
number as sufficient thermodynamic state.

REF-1 selects **TEOS-10** as the production thermodynamic target. Before the MODEL-1 kernel,
seawater forcing should be normalized to enough information to derive/store:

```text
depth_m
sea_pressure_dbar
absolute_salinity_gkg
conservative_temperature_C
```

plus provenance identifying the provider's original salinity/temperature quantities and the
conversion applied.

For inline/manual inputs in schema v1:

- `salinity_profile_psu` means Practical Salinity unless an explicit later schema says otherwise;
- a plain inline `temperature_profile_C` means in-situ ITS-90 temperature;
- provider adapters such as Copernicus must preserve the provider variable meaning and convert
  potential/in-situ temperature deliberately rather than relabel one as the other.

Site latitude/longitude and pressure/depth provide the context needed for TEOS-10 conversions.
The normalized model may then transport Absolute Salinity and Conservative Temperature/potential
enthalpy and evaluate density at the local pressure.

Legacy Knudsen/EOS-80 relations remain useful only inside reference/compatibility comparisons.
They are not the customer-facing thermodynamic default.

See `reference/REF1_NEARFIELD_BAKEOFF.md` for the evidence and rationale.

## 6. Design Mode

Design Mode uses the same normalized config/model stack as time-series runs, but evaluates one forcing snapshot repeatedly while changing geometry/operation.

A design snapshot may come from:

- inline/manual profiles;
- CSV/files;
- a selected timestamp from an already cached provider dataset;
- later, an automatically selected adverse/representative timestamp.

Design candidates should be saved in the ignored workspace rather than committed by default:

```text
workspace/
  design/
    <project-id>/
      <session-id>/
        base.normalized.yaml
        candidates/
          <candidate-id>/
            config.normalized.yaml
            metrics.*
            plots/
        selected.yaml
```

The selected candidate can then be copied/exported as the locked project config for annual simulation.

Design Mode should not fork the physics implementation. It calls the same outlet adapter, solver, field reconstruction and criteria engine used by historical/live runs.

### TIME-1A historical CSV providers and replay-input snapshots

`csv_time_depth_profile` maps the named `temperature_profile_C` (in-situ ITS-90 °C) or `salinity_profile_psu` (Practical Salinity) to an explicitly UTC-timestamped `time, depth_m, value` table. `csv_time_vector_profile` maps `current_profile` to `time, depth_m, u_east_mps, v_north_mps` (ENU, m/s). Whole-second timestamps must be timezone-aware; within one timestamp, all depth levels increase strictly and the selected grid covers 0 m and `site.water_depth_m`. No silent time/depth extrapolation or gap interpolation. File SHA is included in the request/cache identity.

The reusable `plume.history.acquire_history` API returns an indexed history, request/data SHA and provenance, explicit `clock_times`, `available_times` and `missing_by_time`, and can materialize a true `PinnedSnapshot` using `snapshot_at(config,timestamp)` without provider I/O. The current profile can be depth-varying; optional new snapshot field is omitted for legacy static-current pins so existing one-hour identities remain unchanged. Cache JSON and demo CSV/plots belong only in the configured ignored workspace. The normal forcing clock is **start inclusive/end exclusive**, positive whole-second sampling. Schema-v1 `forcing.clock` rejects fractional start/end rather than silently truncating; scalar plant CSV samples preserve microseconds so off-grid readings never masquerade as whole-hour data. File edits invalidate cache by byte SHA, geometry changes do not.

The history source descriptors must be the **original normalized time-varying flow and temperature providers**, not DESIGN-1's locked one-hour constant design controls. TIME-1B will handle Copernicus native potential temperature/native Practical Salinity and convert deliberately at the model boundary, preserving actual requested/used ocean cell. See [TIME_1A.md](TIME_1A.md).

## 7. Copernicus provider

Reuse the proven HeatHandler ideas without coupling the repositories:

- `copernicusmarine` client;
- nearest valid wet-cell search near masked coastal cells;
- record requested and actually used lat/lon/depth;
- record dataset/variable IDs;
- cache exact requests;
- explicit warnings for spatial/depth fallback;
- date-aware product selection where necessary.

Plume additionally needs current components and should support depth-resolved `u/v` when the selected product provides them.

Do not assume global Copernicus resolution is sufficient for a permit-scale coastal site. Provider provenance must make resolution and spatial fallback visible.

## 8. Workspace

Default:

`workspace/`

The entire default workspace is gitignored.

Recommended structure:

```text
workspace/
  _cache/
    providers/
      copernicus/
        <request-hash>/
          data.*
          metadata.json
  projects/
    <project-id>/
      project.yaml
      revisions/
      design/
        <session-id>/
      runs/
        <run-id>/
          manifest.json
          config.normalized.yaml
          inputs/
          results/
            timestep_metrics.*
            fields/
          plots/
          animations/
          logs/
```

### Shared provider cache

`workspace/_cache` is shared across configs/design sessions/runs. An identical provider request should reuse the same immutable cache entry.

The cache key should include all request fields that can change the returned data: provider, dataset/variable, location/bounds, depth selection, time range, temporal aggregation and relevant provider version/options.

### Project persistence

A named customer/site project lives under `workspace/projects/<project-id>/` by default. `project.yaml` is the current local project state; `revisions/` preserves explicitly saved design/config revisions. Customer projects remain gitignored unless the user explicitly exports a portable config.

A portable project config stores the site/provider specification and selected design. Machine-local cache paths and secret values are never required for portability; exact cache/input identities belong in run/design manifests.

### Run directory

A run receives its own immutable-ish result directory. Re-running with changed config should normally create a new run rather than silently overwrite evidence.

At minimum, every run saves:

- normalized config;
- manifest/provenance;
- timestep metrics.

Heavy artifacts are controlled by config.

## 9. Cache invalidation

Use independent cache identities:

- provider cache = normalized external-data request;
- model cache = normalized model/design config + normalized forcing/input identity + Plume model version;
- render cache = model-result identity + rendering options.

Changing geometry must not invalidate Copernicus/provider data. Changing figure styling must not invalidate model results. Changing a locked project design marks prior simulations as stale for the current revision without deleting those runs.

## 10. Output retention policy

The config decides what is saved. Typical switches:

- normalized config / manifest: always;
- provider cache: enabled/disabled;
- forcing snapshots: enabled/disabled;
- timestep metrics: enabled;
- full spatial fields: none / selected cadence / every timestep;
- plots: selected views;
- animation: enabled/disabled;
- report: enabled/disabled.

A fast engineering run may save only metrics and selected frames. A permit package may retain fields, figures and animation.

## 11. Run identity and provenance

Generated `manifest.json` should eventually contain:

- config path and normalized-config digest;
- Plume git SHA/version;
- start/end/cadence or design snapshot identity;
- provider requests and cache digests;
- actual coordinates/depths used;
- source data file digests;
- outlet type/geometry;
- model options;
- criteria;
- warnings;
- output inventory.

No secret value may be copied into the manifest.

## 12. Portability / HeatHandler

Core config and result objects should not mention Streamlit or HeatHandler.

A future HeatHandler integration should be able to:

1. construct/modify a Plume config;
2. call the same headless Plume API;
3. receive normalized metrics/figures;
4. point Plume at a HeatHandler-selected site/provider cache if desired.

This is a design constraint from SPEC-0, not a requirement to build the integration now.
