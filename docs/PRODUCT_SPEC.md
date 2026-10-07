# Plume product specification

**Status:** SPEC-0 product boundary, version 0.1.

## 1. Purpose

Plume is a thermal-discharge digital twin for engineering and permit-support work.

A Plume project combines:

1. **fixed site/outfall geometry**;
2. **time-varying plant forcing**;
3. **time- and depth-varying receiving-water conditions**;
4. a qualified plume model;
5. configurable thermal permit criteria;
6. reproducible metrics, plots and animations.

The central question is not merely "what is the dilution for one case?" but:

> How does the thermal plume change through the operating and environmental envelope, and what does that mean for the customer's permit criteria?

## 2. Primary use cases

### Historical permit assessment
Replay a season/year using historical plant data plus measured or Copernicus ocean data. Produce worst-case, percentile and exceedance statistics plus representative/worst-case plume frames.

### Design comparison
Compare outlet depth, diameter, angle, number of ports or operating strategies against the same environmental time series and permit criteria.

### Operational / digital-twin mode
Later, replace historical providers with live probe/SCADA feeds without changing the solver or criteria interfaces.

### Reusable engine
Keep the physics, providers, runner and criteria UI-independent so HeatHandler or another application can call a light Plume package later.

## 3. Scope

### Core scope

- Thermal discharge only as the customer-facing quantity.
- Fresh or saline receiving water as required for density/buoyancy physics.
- Single round submerged port first.
- Fixed geometry per config/run.
- Flow and discharge temperature varying with time.
- Ambient temperature and salinity varying with depth and time.
- Ambient current vector varying with depth and time when data exist.
- Quasi-steady near-field solves at each forcing timestamp.
- Spatial reconstruction of excess temperature ΔT around the integral plume.
- Configurable permit metrics and annual aggregation.
- Section view, plan view, time-series plots and animations.

### Separate/optional model layers

- Multiport diffuser and plume merging.
- Prescribed-current Brooks/simple far-field transport.
- Bathymetry as a geometric boundary.
- External hydrodynamic model fields for site-scale advection.

### Explicit non-goals

- Building a general CFD solver.
- Solving tidal circulation from bathymetry.
- Replacing FVCOM/ROMS/Delft3D/MIKE/TELEMAC for recirculation, shoreline steering or complex hydrodynamics.
- Pollutant, pH, carbonate, dissolved oxygen or reaction chemistry as Plume product features.
- Claiming regulatory acceptance merely because a result matches PLUMES2.0/Visual Plumes.

## 4. Model architecture

Plume should be layered so each part can be qualified independently.

```text
config
  ↓
providers ─────→ normalized forcing/data contracts
  ↓
time runner ───→ one timestamp / operating state
  ↓
near-field kernel
  ↓
spatial field reconstruction
  ↓
optional far-field layer
  ↓
criteria + metrics
  ↓
plots / animation / reports / API
```

No Streamlit/UI dependency belongs in the core layers.

A future Python package layout may resemble:

```text
src/plume/
  config/
  domain/
  providers/
  model/
  field/
  farfield/
  runner/
  criteria/
  render/
```

This is architectural direction, not a promise that these exact folders must exist.

## 5. Time model

The primary annual runner is **quasi-steady**:

- select a forcing timestamp;
- construct source and ambient profiles;
- solve the plume for that state;
- derive spatial/permit metrics;
- repeat.

This is appropriate while the near-field adjustment time is much shorter than the forcing cadence. A 1-hour year is 8,760 independent near-field states and is intentionally feasible without CFD.

A future far-field model may carry memory between timesteps. If so, that stateful layer must remain distinct from the quasi-steady near-field kernel.

## 6. Required input concepts

### Site

- WGS84 location;
- water depth / bathymetry source;
- optional shoreline/receptor geometry;
- coordinate/datum metadata.

### Outfall

- outlet type;
- port diameter;
- discharge depth below surface (human-facing input);
- port elevation/position after normalization;
- vertical angle;
- azimuth;
- port count/spacing when multiport support is introduced.

### Source forcing

At minimum:

- flow;
- either absolute discharge temperature or process ΔT relative to a defined ambient/reference temperature.

Each forcing may be constant, file-backed, provider-backed or live.

### Ambient forcing

At minimum:

- temperature profile versus depth;
- salinity profile versus depth where density effects matter;
- current vector versus depth if available.

The model must record the actual grid cell, depth levels, interpolation/extrapolation and temporal sampling used by a provider.

## 7. Coordinates and units

User-facing configs use SI by default and intuitive fields such as `discharge_depth_below_surface_m`.

The internal spatial contract should normalize to a fixed local Cartesian frame (east/north/up or equivalent explicitly documented convention) with datum metadata. Solver-specific depth conventions are adapters, not config semantics.

Never silently mix "depth positive down" and "elevation positive up".

## 8. Spatial thermal field

The primary visual target is the supplied mockup: ambient water layers plus nested ΔT contours around the discharge.

The model kernel alone may produce centerline trajectory, width and flux-averaged/centerline properties. A separate **field reconstruction** must convert that integral state into a physically defined cross-plume temperature profile.

The contour renderer may not invent decorative plume shapes. Similarity profile, centerline/mean relation and contour geometry must be explicit and reference-tested.

Expected products include:

- vertical section ΔT contours;
- plan-view ΔT contours;
- optional 3-D/volume representation;
- surface footprint/hotspot when the plume reaches the surface;
- animation with a stable colour scale and permit threshold overlay.

## 9. Permit criteria

Permit requirements vary by customer and belong in config, not hard-coded model logic.

The criteria layer should be able to express, over time:

- ΔT threshold extent (for example 2 °C);
- maximum horizontal distance/width/area/volume above a threshold;
- maximum surface excess or absolute temperature;
- temperature at a receptor;
- threshold at/after a mixing-zone boundary;
- exceedance hours/days;
- longest continuous exceedance;
- annual maximum, P95/P99 and worst timestamp.

Criteria should report both the raw physical metric and pass/fail logic so regulatory wording remains auditable.

## 10. Data providers

The solver consumes normalized data, not vendor APIs.

Initial provider kinds:

- `constant`;
- `inline_profile`;
- `csv`;
- `copernicus`.

Future providers:

- probe/CTD/ADCP;
- plant historian / SCADA;
- external hydrodynamic model;
- customer database/API.

Every provider result must carry provenance: source, request, time/depth coverage, actual location/depths used, cache identity and warnings.

Copernicus patterns already proven in HeatHandler should be reused conceptually: UI-independent client, nearest valid wet-cell handling, depth metadata and local cache. Plume should not depend on HeatHandler itself.

## 11. Bathymetry and far field

Bathymetry can be used early as:

- water-depth input;
- section/plan background;
- bottom-intersection boundary.

Bathymetry alone does not tell us the current field.

For complicated coastal sites, current fields should come from observations or an external hydrodynamic model. Plume may then advect its thermal field using those prescribed currents.

A simple Brooks/prescribed-current far-field layer is in scope after near-field qualification. Full site hydrodynamics is not.

## 12. Reproducibility

Every run must create a manifest that can answer:

- which config/schema version;
- which Plume commit/model version;
- which provider datasets and exact requests;
- actual coordinates/depths/times used;
- cache/input digests;
- solver/reference qualification state;
- criteria;
- generated outputs.

A run with identical normalized inputs should be reproducible independent of UI.

## 13. Reference and validation strategy

External/reference implementations are evidence, not runtime dependencies by default.

Qualification ladder:

1. deterministic conservation/invariant tests;
2. canonical PLUMES2.0 comparisons;
3. Visual Plumes/UM3 implementation comparisons where useful;
4. independent literature/experiment comparisons;
5. site measurements when available.

Calibration cases and hold-back verification cases must be separate.

## 14. v1 success definition

A useful first product slice is complete when one config can:

1. describe one single-port outfall;
2. ingest a historical time series of flow/discharge temperature and depth-resolved ambient forcing;
3. run the qualified near-field solver across the selected period;
4. reconstruct one or more ΔT fields/contours;
5. compute configurable permit metrics for every timestamp;
6. produce annual summary plots and an animation;
7. preserve a reproducible local run manifest;
8. run headlessly as a Python API/CLI so a future HeatHandler integration is thin.
