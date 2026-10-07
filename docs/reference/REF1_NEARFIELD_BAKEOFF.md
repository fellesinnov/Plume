# REF-1B — single-port near-field mechanism bakeoff

Date: 2026-10-07

Status: **decision record for REF-1 continuation; not physical validation**.

Pinned source identities are in `tests/reference/reference-lock.json`. This document compares the
mechanisms needed by the first Plume product kernel. It deliberately excludes multiport merging,
far field, chemistry and spatial similarity-profile reconstruction from MODEL-1.

## 1. Question

What should MODEL-1 inherit from the available UM3/PLUMES implementations, what should remain a
reference-only compatibility path, and what should Plume replace with a physically stronger
formulation?

The answer is mechanism-specific. There is no single reference implementation that should be
copied wholesale.

## 2. Evidence boundary

### Ebb Carbon Plumes_Public

Pinned at `9791c80ff94f706603df0ae473667ccdffd359db`.

Role: **MIT-licensed adaptation candidate**.

Particularly relevant files are pinned by blob identity in `reference-lock.json`:

- `nearfield/state.py`;
- `nearfield/solver.py`;
- `nearfield/entrainment.py`;
- `nearfield/terminate.py`;
- `seawater.py`;
- the near-field validation suite and case18/case19/case11 traces.

Ebb is not treated as physical truth. Its strongest value is that it makes decoded executable
behaviour, alternative formulations and known divergences explicit rather than hiding them behind
one output.

### SFEI Visual-Plumes-Models

Pinned at `99283a481a84902ab248fcf3b6041b484daa1c1e`.

Role: **GPL-3.0 external behavioural/source oracle**.

The source independently corroborates several UM3 implementation details found by Ebb, while its
licence and legacy stepwise structure make it a worse direct product-code source for Plume.

### PLUMES executable evidence

The checked-in executables/traces remain immutable regression references. REF-1A established that
the two shipped examples have identical near-field tables but different far-field settings, so
executable evidence is only used when the compared inputs/session state are controlled.

### Independent literature

Key external references used in this decision:

- US EPA Visual Plumes 4th ed. text:
  https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P1001G6B.TXT
- US EPA Dilution Models 3rd ed. text:
  https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=20008OUL.TXT
- Fan (1967), Caltech experimental thesis:
  https://thesis.caltech.edu/9290/
- Lee & Cheung (1991), buoyancy-dominated heated jets in weak current:
  https://researchportal.hkust.edu.hk/en/publications/mixing-of-buoyancy-dominated-jets-in-a-weak-current/
- Seckin et al. (2026), UM3/DKHW against Fan and Lee-Cheung:
  https://doi.org/10.1016/j.dynatmoce.2026.101662
- official TEOS-10:
  https://www.teos-10.org/

## 3. Mechanism matrix

| Mechanism | Ebb | SFEI / PLUMES evidence | Independent evidence | REF-1 decision |
|---|---|---|---|---|
| Lagrangian control-volume state | conserved mass, vector momentum, T, S and position; continuous ODE | SFEI advances the same physical balances stepwise | UM3 documented as Lagrangian conservation model | **ADAPT Ebb architecture** |
| Source contraction | `b0=(D/2)sqrt(c)`, velocity through contracted area | same relation in SFEI initialization | executable test23/test25 pair independently identifies it | **ADAPT** |
| Element stretching | `h proportional to |V|`; radius derived algebraically | SFEI explicitly rescales element height by velocity ratio each step | executable trace measurement supports relation | **ADAPT relation, not legacy stepping** |
| Zero-current aspiration | alpha ≈ entered value, default 0.1 | SFEI default aspiration coefficient 0.1 | Taylor/aspiration entrainment is established model component | **ADAPT with coefficient explicit** |
| Current-relative shear | relative plume/ambient velocity | SFEI code uses ambient-relative velocity inside aspiration | Fan crossflow analysis also uses vector velocity difference | **ADOPT** |
| Forced/cross-current entrainment | Ebb's `Um3Entrainment` matches executable; naive published-sum PAE is worse for parity | SFEI source independently shows the coupled aspiration/cylinder structure | EPA theory describes PAE, including growth/cylinder/curvature | **ADAPT UM3 reference closure; keep published PAE as qualification candidate** |
| Single-plume curvature contribution | Ebb parity closure sets curvature contribution to zero because SFEI geometry makes its dot product zero and executable traces improve with it off | SFEI implementation corroborates the inert term | EPA 3rd ed. says curvature can be important physically | **DO NOT promote zero-curvature parity into physical truth; discriminate with physical data** |
| Temperature/salinity mixing | Ebb conserves `m*T` and `m*S` | SFEI mass-averages T/S | TEOS-10 provides thermodynamically consistent salinity/density and Conservative Temperature | **KEEP conservation architecture; upgrade thermodynamics for Plume** |
| Density | EOS-80 product default, Knudsen executable-parity option | SFEI default equilibrium density is the same old Knudsen-family relation | TEOS-10 superseded EOS-80 as official seawater thermodynamics | **PLUMES density only for reference parity; production target TEOS-10** |
| ODE / step controller | adaptive `solve_ivp` + dense output; executable step controller excluded from physics | SFEI reproduces legacy adaptive step logic | no physical reason to reproduce GUI program stepping | **ADAPT continuous integration, not the legacy controller** |
| Surface/seabed/oscillation events | explicit geometry/event layer | SFEI interleaves termination in loop | boundary events are product policy, not conservation law | **ADAPT separation; define Plume policy explicitly** |
| Similarity profile / centreline | separate `crossplume` module | SFEI exposes same three Visual Plumes profiles | profile choice directly changes peak ΔT | **OUT of MODEL-1; FIELD-PROFILE-1 owns** |
| Multiport merging | extensive but still mechanism-sensitive | SFEI has legacy merged-plume logic | independent coalescing-plume theory exists | **OUTLET-2** |
| Brooks far field | separate Ebb layer | separate SFEI layer | scope depends on hydrodynamics | **FARFIELD-1** |

## 4. The key entrainment finding

A literal implementation of:

`Taylor entrainment + all published projected-area terms`

is **not** the best representation of what the UM3 implementation actually computes.

The SFEI source and Ebb reconstruction independently expose why. In the UM3 implementation, part of
the cross-current cylinder contribution is folded into the effective aspiration velocity. The
matching reduction in Taylor/aspiration entrainment cancels that cylinder contribution
algebraically in the corresponding regime. Adding the published cylinder term again on top of an
unreduced Taylor term double-counts part of the effect.

That is not a reason to call the implementation physically superior to the documented equations.
It is a reason to preserve two concepts during qualification:

1. **UM3 reference closure** — the decoded behaviour needed for faithful software comparison;
2. **published/physical PAE candidate** — the documented growth/cylinder/curvature formulation,
   evaluated against independent experiments rather than judged by executable parity.

MODEL-1 should not expose both as casual customer-facing knobs. The alternative exists to settle
the physics, not to make every project user choose a plume theory.

## 5. Canonical single-port software evidence

### E-NF-0 — test23

Single port, zero near-field current, no merging. It isolates Taylor entrainment and source/state
relations.

Ebb's pinned validation reports:

- jet-phase dilution mean absolute relative error about **0.31%** against the PLUMES trace;
- pre-trapping rise also below the upstream 0.5% mean-error reference bar used there;
- temperature and salinity transport agree much more tightly because they are conservation
  quantities rather than closures;
- later oscillatory/trapping behaviour drifts more strongly when Ebb uses modern EOS-80 instead
  of the executable's old density relation.

This case is a **software/mechanism reference**, not physical hold-back.

### E-NF-C — test28/test27/test29/test30

Same single-port mechanism with near-field current 0.01 / 0.02 / 0.05 / 0.10 m/s.

The sweep is important because zero-current cases cannot discriminate absolute from
ambient-relative shear. Ebb's current implementation reports jet-phase error roughly
0.34–0.88% across the sweep, while the source tests show that adding the curvature contribution
used by the literal projected-area decomposition worsens all four software comparisons.

Again: this proves what the executable/SFEI lineage does. It does **not** prove that inert curvature
is the best physical treatment.

### E-NF-T — case11

Clean slow single-port case with trapping/oscillation and no multiport merging. It is retained for
termination/trajectory behaviour, not for chemistry.

## 6. Thermodynamics decision for Plume

Plume is a **thermal** digital twin, so density/heat treatment is not a peripheral implementation
detail.

TEOS-10 is the current official seawater thermodynamic standard and explicitly supersedes EOS-80.
It uses Absolute Salinity and Conservative Temperature / potential enthalpy and provides
pressure-aware in-situ density.

Therefore REF-1 recommends the following MODEL-1 contract:

- provider/user inputs may remain familiar practical salinity + temperature where appropriate;
- before the physics kernel, normalize seawater thermodynamics to:
  - Absolute Salinity `SA_gkg`;
  - Conservative Temperature `CT_C`;
  - sea pressure `p_dbar` at the sampled depth;
- transport salt and heat in conserved form;
- use Conservative Temperature / potential enthalpy as the heat-content state rather than treating
  in-situ temperature as an exactly conserved passive scalar;
- calculate plume/ambient density through TEOS-10;
- derive in-situ temperature for report/permit output at the local pressure;
- retain EOS-80/Knudsen only in the **reference harness or explicit compatibility tests**, not as
  the customer-facing physical default.

The official GSW-Python implementation is a suitable dependency candidate and ships binary wheels;
it should be used as an unmodified dependency rather than vendored.

This decision deliberately improves on Ebb rather than copying it.

## 7. Coordinate/convention decision

Plume should not inherit the arbitrary reference-model x/y bearing convention.

Canonical model coordinates for the product:

- local tangent Cartesian **ENU**:
  - `+x = east`;
  - `+y = north`;
  - `+z = up`;
- free surface is `z = 0` for the local design snapshot;
- depth is separately represented positive downward;
- outfall azimuth is navigation convention: **0° = north, 90° = east, clockwise**;
- vertical outlet angle is **0° horizontal, positive upward**;
- provider current is already `u_east_mps, v_north_mps`.

Reference adapters own conversion from a PLUMES/SFEI local axis convention to this contract.
No reference convention is allowed to leak through the normalized product API.

## 8. Physical calibration and hold-back split

The physical evidence set must be independent of PLUMES/Ebb/SFEI traces.

### Formulation/calibration set

**Fan (1967)** is the primary formulation set for current-affected round jets because the public
Caltech work contains trajectory, width and dilution experiments and historically underpins PAE
development. It contains both stratified-stagnant and uniform-crossflow cases.

Use it to:

- discriminate reference-UM3 versus literal published-PAE behaviour;
- confirm trajectory, width and dilution trends;
- if a coefficient truly requires calibration, freeze it here only.

Do not tune against the later hold-back.

### Hold-back set

**Lee & Cheung (1991)** is reserved as the primary physical hold-back because it is especially
relevant to Plume: vertical **heated**, buoyancy-dominated jets in crossflow, across weak-current,
transition and farther-current regimes.

The recent Seckin et al. (2026) comparison strengthens this choice: it evaluated UM3 against
99 mostly momentum-dominated Fan data and 107 buoyancy-dominated Lee-Cheung data and reports
materially better UM3 performance on Fan than on Lee-Cheung. The harder, more product-relevant
dataset therefore belongs on the hold-back side of the line.

**No coefficient or closure choice may be tuned on Lee-Cheung and then reported as verification.**

### Current evidence limitation

The papers/landing pages establish the datasets and their role, but REF-1 has not yet obtained a
clean machine-readable copy of the complete experimental rows with redistribution/provenance
clear. Until that exists:

- Fan/Lee-Cheung are **qualified physical evidence targets**, not committed numeric goldens;
- no values are digitized from plots merely to make a test;
- MODEL-TOL-1 remains open.

## 9. MODEL-1 implementation recommendation

If REF-1 closed today, the starting implementation would be:

1. **adapt the Ebb MIT single-port LCV structure**, with attribution;
2. retain conserved mass + vector momentum and the algebraic element-stretching geometry;
3. use an internal **UM3-reference entrainment closure** derived from the Ebb MIT implementation
   for software regression;
4. retain a documented published-PAE qualification implementation until Fan/Lee-Cheung evidence
   chooses the physical production closure;
5. **replace Ebb's seawater thermodynamics with TEOS-10** for the production path;
6. carry heat as Conservative Temperature/potential enthalpy rather than raw in-situ temperature;
7. use ENU coordinates and normalized vector current;
8. use adaptive continuous ODE integration and explicit boundary/oscillation events;
9. do **not** bring over chemistry, Brooks, merging or similarity-profile reconstruction.

This gives Plume a clean path to be more physically current than PLUMES while preserving exact
reference comparability where it is useful.

## 10. What REF-1B retires and what remains

Retired for MODEL-1 starting architecture:

- direct-reuse source: **Ebb**, not SFEI;
- SFEI role: **oracle only**;
- conserved LCV architecture;
- source contraction relation;
- element-stretching relation;
- current-relative shear;
- continuous solver rather than legacy step-controller parity;
- explicit separation of model coordinates from reference coordinates;
- legacy PLUMES density is **not** the production default.

Still open before REF-1 integration:

- executable SHA-256 and controlled same-input build-to-build run for `PLUMES-REF-1`;
- obtain/encode enough independent Fan/Lee-Cheung numerical evidence to discriminate the physical
  entrainment candidates without contaminating hold-back;
- decide the production entrainment closure from that physical evidence;
- define MODEL-TOL-1 only after the independent error distribution exists;
- similarity-profile decision remains `FIELD-PROFILE-1`, not MODEL-1.
