# Configuration, providers and workspace

**Status:** SPEC-0 contract draft. No implementation is implied yet.

## 1. Principles

- Config is the durable description of a Plume project/run.
- UI state must be serializable into the same schema.
- YAML and JSON may both be accepted; the normalized schema is authoritative.
- SI is the default.
- Secrets never appear in config.
- Paths are relative to the config file unless explicitly absolute.
- Downloaded/provider data and generated outputs are local artifacts, not source.
- Provider-specific data is normalized before it reaches the model.

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

Provider/file details may evolve behind those concepts.

## 3. Forcing references

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

## 4. Normalized provider contracts

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

## 5. Copernicus provider

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

## 6. Workspace

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
  runs/
    <project-id>/
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

`workspace/_cache` is shared across configs/runs. An identical provider request should reuse the same immutable cache entry.

The cache key should include all request fields that can change the returned data: provider, dataset/variable, location/bounds, depth selection, time range, temporal aggregation and relevant provider version/options.

### Run directory

A run receives its own immutable-ish result directory. Re-running with changed config should normally create a new run rather than silently overwrite evidence.

At minimum, every run saves:

- normalized config;
- manifest/provenance;
- timestep metrics.

Heavy artifacts are controlled by config.

## 7. Output retention policy

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

## 8. Run identity and provenance

Generated `manifest.json` should eventually contain:

- config path and normalized-config digest;
- Plume git SHA/version;
- start/end/cadence;
- provider requests and cache digests;
- actual coordinates/depths used;
- source data file digests;
- model options;
- criteria;
- warnings;
- output inventory.

No secret value may be copied into the manifest.

## 9. Portability / HeatHandler

Core config and result objects should not mention Streamlit or HeatHandler.

A future HeatHandler integration should be able to:

1. construct/modify a Plume config;
2. call the same headless Plume API;
3. receive normalized metrics/figures;
4. point Plume at a HeatHandler-selected site/provider cache if desired.

This is a design constraint from SPEC-0, not a requirement to build the integration now.
