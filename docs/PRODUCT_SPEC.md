# Plume product specification

**Status:** SPEC-0 product boundary, version 0.2.

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

Accuracy matters more than parity with any one legacy/reference implementation.

## 2. Primary use cases

### Design Mode — choose the outlet first

Before annual simulation, load one representative or deliberately adverse water column plus one source operating state and rapidly explore outlet geometry/operation.

Typical knobs:

- discharge depth/elevation;
- outlet type;
- diameter;
- vertical angle;
- azimuth;
- port count/spacing when the selected model supports multiport;
- flow;
- absolute discharge temperature or process ΔT.

Design Mode should show permit-relevant metrics and plume plots immediately enough for engineering comparison. The selected design is saved as a normal versioned project config, then reused unchanged for historical/digital-twin analysis.

The design profile can initially be inline or file-backed. Later it may be selected from Copernicus/provider history, such as a worst/representative timestamp.

### Historical permit assessment
Replay a season/year using historical plant data plus measured or Copernicus ocean data. Produce worst-case, percentile and exceedance statistics plus representative/worst-case plume frames.

### Operational / digital-twin mode
Later, replace historical providers with live probe/SCADA feeds without changing the solver or criteria interfaces. Measurements can be compared with the model and may support controlled calibration, while preserving independent verification data.

### Reusable engine
Keep the physics, providers, runner and criteria UI-independent so HeatHandler or another application can call a light Plume package later.

## 3. Scope

### Core scope

- Thermal discharge only as the customer-facing quantity.
- Fresh or saline receiving water as required for density/buoyancy physics.
- Single round submerged port as the first implemented outlet model.
- **Outlet abstraction from the start** so future multiport, vertical/horizontal and near-surface/surface discharge geometries can be added without redesigning configs/runners.
- Fixed geometry per locked config/run.
- Flow and discharge temperature varying with time.
- Ambient temperature and salinity varying with depth and time.
- Ambient current vector varying with depth and time when data exist.
- Quasi-steady near-field solves at each forcing timestamp.
- Spatial reconstruction of excess temperature ΔT around the integral plume.
- Configurable permit metrics and annual aggregation.
- Section view, plan view, time-series plots and animations.

### Separate/optional model layers

- Multiport diffuser and plume merging.
- Other outlet types where reference/physics evidence supports them.
- Prescribed-current Brooks/simple far-field transport.
- Bathymetry as a geometric boundary.
- External hydrodynamic model fields for site-scale advection.

### Explicit non-goals

- Building a general CFD solver.
- Solving tidal circulation from bathymetry.
- Replacing FVCOM/ROMS/Delft3D/MIKE/TELEMAC for recirculation, shoreline steering or complex hydrodynamics.
- Pollutant, pH, carbonate, dissolved oxygen or reaction chemistry as Plume product features.
- Claiming regulatory acceptance merely because a result matches PLUMES2.0, Visual Plumes or any other software.

## 4. Model architecture

Plume should be layered so each part can be qualified independently.

```text
config
  ↓
providers ─────→ normalized forcing/data contracts
  ↓
design snapshot OR time runner
  ↓
outlet adapter
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
  outlets/
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

Design Mode is simply a one-timestamp/snapshot use of the same normalized model/criteria stack, not a separate physics implementation.

## 6. Required input concepts

### Site

- WGS84 location;
- water depth / bathymetry source;
- optional shoreline/receptor geometry;
- coordinate/datum metadata.

### Outfall

Stable/common fields should include:

- outlet type;
- discharge position/depth;
- vertical angle;
- azimuth/orientation.

Type-specific geometry belongs behind the outlet adapter. Examples include:

- single round port: diameter;
- multiport diffuser: port diameter/count/spacing/layout;
- future surface/near-surface outlet: geometry appropriate to that model.

The schema should not pretend unsupported outlet types are physically implemented merely because they can be represented.

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

Every run/design evaluation must be able to answer:

- which config/schema version;
- which Plume commit/model version;
- which provider datasets and exact requests;
- actual coordinates/depths/times used;
- cache/input digests;
- outlet geometry/model;
- solver/reference qualification state;
- criteria;
- generated outputs.

A run with identical normalized inputs should be reproducible independent of UI.

## 13. Reference and validation strategy

No external program is holy. Use a **reference ensemble**:

1. deterministic conservation/invariant tests;
2. PLUMES2.0 executable traces where relevant;
3. SFEI Visual Plumes/UM3 as an external behavioural oracle where useful;
4. the MIT Ebb Carbon PLUMES2.0 port as a secondary implementation and potentially reusable source after review;
5. independent literature/experiment comparisons;
6. site measurements/probes when available.

Differences between references are evidence to investigate, not something to average away.

Calibration cases and hold-back verification cases must be separate. Live/site measurements used for calibration must leave independent periods/locations for verification.

## 14. v1 success definition

A useful first product slice is complete when Plume can:

1. represent and run a single-round-port outfall behind the extensible outlet contract;
2. load one snapshot and compare design variants, then save the chosen geometry as a normal config;
3. ingest a historical time series of flow/discharge temperature and depth-resolved ambient forcing;
4. run the qualified near-field solver across the selected period;
5. reconstruct one or more ΔT fields/contours;
6. compute configurable permit metrics for every timestamp;
7. produce annual summary plots and an animation;
8. preserve a reproducible local run manifest;
9. run headlessly as a Python API/CLI so a future HeatHandler integration is thin.
