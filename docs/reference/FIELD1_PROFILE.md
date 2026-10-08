# FIELD-1 — spatial near-field temperature profile and coordinates

**Status:** provisional FIELD-1 formulation. This is a deterministic, reference-informed reconstruction contract, **not** physical validation or a permit-accepted prediction. Physical field-profile qualification remains open under `FIELD-PROFILE-1`.

## 1. Scope and evidence

FIELD-1 turns the MODEL-1 bulk, mass-averaged near-field `Trajectory` into a **three-dimensional, finite near-field tube** and samples physical vertical-section and fixed-depth horizontal-plan slices. No Streamlit dependency, provider downloads, far-field advection, plume merging, site bathymetry or annual/time runner is introduced.

Primary reference: US EPA, *PLUMES2.0 Model Theory and User Manual*, EPA/600/B-24/339 (December 2024), section 3.3.1, pp. 10–11:

https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P101DSLB.TXT

The report describes Kannberg/Davis's bounded **3/2-power radial concentration profile** and derives the **round-plume centerline/average limiting factor of 3.89** under a uniform/top-hat velocity approximation. It also cautions that the factor approaches 1 near the source, varies along the plume and is approximate in depth-varying backgrounds. We reuse the *functional form*, not any external implementation source code.

## 2. Profile and dimensional interpretation

Let `b` be MODEL-1's element radius, `r` its perpendicular distance to the centerline, and `q=r/b`.

For fully developed round-plume, the unscaled shape is:

```text
phi(q) = (1 - q^(3/2))^2    for 0 <= q <= 1;  0 outside
mean(phi) = 2 * integral_0^1 phi(q) q dq = 9/35
K = 35/9 = 3.888888...  [centerline / circular area mean]
w_developed(q) = K * phi(q)
```

This area-mean equality assumes a circular cross section with top-hat velocity; it does **not** prove that the LCV's transport-weighted and cross-section-area-weighted mean concentrations coincide under a real velocity profile.

For the near-source interval, a direct application of K to an unmixed source (`D=1`) would create impossible peak tracer fractions. FIELD-1 chooses a **provisional bounded blend**:

```text
lambda(D) = clip((D - 1)/(K - 1), 0, 1)
w(q,D) = (1-lambda) + lambda * K * phi(q)   for 0 <= q <= 1
w = 0 outside
```

Therefore the circular area mean is **exactly 1**, and the peak multiplier is `min(D,K)` for `D >= 1`. This mixing law is a **safety-motivated modelling assumption**, *not* a measured near-source evolution, EPA-prescribed interpolation, or calibrated spatial profile. It will need actual cross-plume evidence and sensitivity testing before the physical FIELD gate closes.

## 3. Temperature and salinity perturbations

MODEL-1 conserves Absolute Salinity (`SA`, g/kg) and Conservative Temperature (`CT`, deg C). FIELD-1 samples bulk anomalies relative to the **ambient at the corresponding centerline depth**:

```text
delta_CT_bulk(s) = CT_plume(s) - CT_ambient(depth_centerline(s))
delta_SA_bulk(s) = SA_plume(s) - SA_ambient(depth_centerline(s))
```

The spatial profile is then applied to **both** anomalies using `w(q,D(s))`. At a field cell `(east,north,depth)`, these anomalies are added to the *ambient properties at that cell's depth*, never the ambient at the centerline depth, yielding `SA_cell` and `CT_cell`.

The injected MODEL-1 `Thermodynamics.in_situ_temperature_C` boundary maps `(SA_cell,CT_cell,depth)` to in-situ temperature. The reported heat field is:

```text
delta_T_in_situ_C(cell) = t(SA_cell, CT_cell, depth)
                          - t(SA_ambient, CT_ambient, depth)
```

This is **in-situ temperature excess relative to local ambient**, not raw `delta_CT` or `temperature above surface ambient`. In stratified water the local perturbation may not have the same conservation interpretation as the bulk scalar under nonlinear TEOS-10. These are explicit model limitations, not assumptions silently repaired by the renderer.

## 4. Coordinates and finite support

- Cartesian local model frame: **east, north, up** in metres; water surface is `z=0`.
- Positive-down depth is `depth_m=-z_up_m`; temperature is local-depth referenced.
- Nearest **finite 3-D centerline segment** determines approximate normal distance and linearly interpolated `b`, `D`, `delta_CT`, `delta_SA`. A 2-D centerline projection is expressly forbidden for physical section samples: an off-plane plume must not appear centered in the section.
- Points outside a radius or ahead of/beyond the modeled trajectory's axial endpoints are **not supported**. No invented spherical end caps, downstream plume, or persistent ambient anomaly.
- At self-intersecting trajectory segments, the nearest physical branch wins; mass from overlapping tubes is not added. That overlap and strong curvature require later dedicated physics/evidence.
- The section is a true physical plane through the port, with a specified or derived horizontal heading. Plan view is a **fixed-depth slice**, not a maximum-temperature projection through the water column.
- `FieldValues.modeled` marks support. Zeros outside it are an **absence of near-field prediction**, *not* proof the far-field thermal effect is zero.

## 5. Plotting contract

`plume.field` implements pure NumPy reconstruction and accesses the core thermodynamics abstraction. `plume.render` is an **optional** Matplotlib consumer, installed as `plume-engine[plot]`; it cannot alter physics or fetch providers.

The initial plot theme intentionally visualizes **warm** excess only; if a cold anomaly is supplied it **raises** instead of falsely drawing no plume. A signed warm/cold palette is future renderer work, not a restriction on the headless field output. The renderer displays the ambient water-column background on a separately labelled in-situ temperature colour scale and the thermal plume on a separately labelled `delta_T` colour scale. It outlines the **calculated** configured threshold (default 2 deg C), never a manufactured drawn contour. It must label the near-field qualification limitations.

Generated customer/demo PNG/SVG files belong in gitignored `workspace/`. The synthetic diagnostic preview produced during FIELD-1 uses an **illustrative manufactured trajectory**, not a full MODEL-1/GSW simulation. It is not checked in as a golden physical figure.

## 6. Discriminating evidence and open gates

Sandbox fixture tests cover:

- analytic `9/35` mean and source concentration cap for the 3/2-power profile;
- precise centerline and radial anomalies for constant ambient;
- early/late axial end cap and radial support rejection;
- sensitivity to radius and dilution;
- an off-section plume refusing to project a false hotspot onto the section;
- local ambient depth handling, explicit full-column coverage (no extrapolation) and salinity transport;
- curved 3-D nearest-segment choice, numerical chunk invariance, invalid-sign/NaN rejection;
- section heading, plan depth and optional Matplotlib separation;
- a separately optional official-GSW conversion smoke when the package is installed.

The focused sandbox verifies **mathematical implementation of the named assumptions**, not their independent physical applicability. A complete checkout test against the actual MODEL-1 `NearFieldSolution` and numeric real-GSW smoke remain owed. Strongly stratified/nonmonotonic ambient, velocity-weighted cross-section behavior, near-source-profile blending, curvature and laboratory/field isopleths remain open physical evidence.

No `References/` files were modified. `FIELD-PROFILE-1` stays **OPEN** until a defensible published/observed cross-plume comparison and independent hold-back are available. Similarly `MODEL-CLOSURE-1`/`MODEL-TOL-1` remain open; FIELD-1 does not create a production-qualified plume.
