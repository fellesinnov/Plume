# Submerged Thermal Outfall Screening Tool

A fast, transparent **concept-design** model for deciding whether a single submerged pipe looks like a robust
"garden-hose" discharge or whether the project should move to CORMIX/PLUMES, a diffuser study, and/or
site-specific far-field hydrodynamics.

> **Important:** this is a screening and design-comparison model. It is not a permitting model and should not
> be represented as equivalent to CORMIX, CorJet, PLUMES2.0/UM3, Delft3D, MIKE, TELEMAC, or validated CFD.

## 1. What is implemented

`outfall_screen.py` solves a steady 3-D integral round jet/plume with:

- volume entrainment;
- vector momentum;
- buoyancy from seawater density differences;
- conservative temperature and salinity mixing;
- optional ambient current magnitude and direction;
- optional linear T/S stratification;
- surface, bottom, horizontal-clearance, and neutral-buoyancy termination;
- bulk and approximate centerline dilution;
- GREEN / AMBER / RED screening;
- single-case plots;
- batch runs from CSV;
- a global T/S/current envelope sweep.

The density equation is UNESCO/EOS-80 sigma-t at atmospheric pressure. This is intentionally similar in spirit
to legacy CORMIX/PLUMES density treatment and avoids requiring TEOS-10/GSW for the prototype.

The shear-entrainment closure is Jirka/CorJet-inspired. Default Gaussian coefficients are:

- `alpha_jet_gaussian = 0.055`
- `alpha_plume_increment_gaussian = 0.6`
- limiting plume local Froude number `4.66`

The approximate top-hat conversion is `sqrt(2)`. These values are exposed so the model can be compared and
calibrated against CORMIX/CorJet.

## 2. Installation

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Run one case

```bash
python outfall_screen.py run \
  --flow 4000 \
  --diameter 0.8 \
  --sea-temp 20 \
  --delta-t 10 \
  --depth 15 \
  --port-height 1.6 \
  --angle 15 \
  --plot example_outputs/baseline.png \
  --profile-csv example_outputs/baseline_profile.csv \
  --json example_outputs/baseline_summary.json
```

Useful optional inputs include:

```text
--salinity 35
--discharge-salinity 35
--angle 0
--current 0.3
--current-direction 90
--temp-gradient 0.0
--salinity-gradient 0.0
--clearance 100
--allowed-delta-t 1
--design-factor 1.5
```

Current direction is relative to the outlet in plan:
`0° = co-flow`, `90° = crossflow`, `180° = counterflow`.

## 4. Run the verification matrix

```bash
python outfall_screen.py batch test_cases.csv \
  --out example_outputs/test_results.csv \
  --plots example_outputs/test_plots
```

The supplied cases deliberately isolate different physics:

- T01-T08: flow, depth and diameter/velocity;
- T09-T11: current and crossflow;
- T12: outlet vertical angle;
- T13-T15: absolute temperature and salinity;
- T16: stratification;
- T17: large salinity-density contrast;
- T18: 20,000 m3/h concept case;
- T19: near-neutral jet anchor;
- T20: vertical plume anchor.

## 5. Run a global environmental envelope

This is a **screening envelope**, not proof of worldwide permitting compliance.

```bash
python outfall_screen.py envelope \
  --flow 4000 \
  --diameter 0.8 \
  --delta-t 10 \
  --depth 15 \
  --port-height 1.6 \
  --angle 15 \
  --out example_outputs/global_envelope.csv
```

The standard sweep runs:

- sea temperature = 0, 10, 20, 30 C;
- salinity = 30, 35, 40 PSU;
- current = 0, 0.1, 0.3, 0.5 m/s;
- co-, cross-, and counterflow where current is non-zero.

It intentionally gives **no atmospheric heat-loss credit** and no far-field diffusion.

## 6. Screening logic

For a thermal discharge:

```text
required dilution = process delta-T / allowed receiving-water delta-T
green design dilution = required dilution x design factor
```

Default:

```text
allowed delta-T = 1 C
design factor = 1.5
```

Therefore a +10 C process rise gives:

```text
minimum criterion = 10:1 centerline dilution
GREEN design target = 15:1 centerline dilution
```

The model reports:

- `GREEN`: design dilution reached with path/geometric margin and no applicability warning;
- `AMBER`: criterion may be reached, but margin or model-applicability concerns remain;
- `RED`: required dilution not reached before modeled near-field termination.

This GREEN/AMBER/RED logic is an **internal screening proposal**, not a regulation.

## 7. CORMIX / CorJet comparison workflow

### 7.1 Run the same case in CORMIX1

Map the case fields approximately as follows:

| This tool | CORMIX1 concept |
|---|---|
| `water_depth_m` | local water depth HD |
| `port_height_m` | H0 |
| `diameter_m` | D0 |
| calculated outlet velocity | U0 |
| `vertical_angle_deg` | THETA |
| current/outlet relative direction | SIGMA / ambient-current orientation |
| `sea_temp_C`, salinity | ambient density inputs |
| sea T + delta-T, discharge salinity | effluent density inputs |

CORMIX uses additional receiving-water geometry and regulatory inputs that this screening tool deliberately
does not reproduce.

### 7.2 Export/copy a CORMIX profile

Create:

```text
cormix_profiles/T01_baseline.csv
```

with:

```text
x_m,y_m,z_m,dilution_centerline
0,0,1.0,1.0
...
```

`y_m` is optional. If absent, it is assumed zero.

### 7.3 Overlay

```bash
python compare_cormix.py compare \
  --cases test_cases.csv \
  --case-id T01_baseline \
  --cormix cormix_profiles/T01_baseline.csv \
  --plot example_outputs/T01_overlay.png
```

The script reports:

- log-RMSE of dilution;
- dilution MAPE;
- vertical trajectory RMSE;
- normalized trajectory error.

### 7.4 Calibrate across several cases

Save CORMIX profiles as `<case_id>.csv`, then:

```bash
python compare_cormix.py calibrate \
  --cases test_cases.csv \
  --profiles-dir cormix_profiles \
  --out example_outputs/calibration_result.json
```

The calibration only adjusts four defensible closure/mapping parameters:

1. `alpha_scale` — primary bulk dilution rate;
2. `centerline_ratio_asymptote` — bulk-to-centerline conversion;
3. `crossflow_entrainment` — added mixing from transverse current;
4. `drag_coefficient` — crossflow trajectory bending.

Bounds are intentionally narrow to avoid turning the model into a curve-fitting machine.

**Do not calibrate all 20 cases and call that validation.** A better workflow is:

- use T19 + T20 + 2-3 current cases + 2-3 ordinary thermal cases for calibration;
- hold back shallow-water, extreme salinity, stratification, and high-flow cases for verification;
- compare a subset independently in PLUMES2.0.

## 8. Recommended calibration sequence

### A. Pure/near-neutral jet
Use T19 first.

Tune `alpha_scale` only until bulk/centerline dilution growth is reasonable.

### B. Strong buoyant plume
Use T20.

If the trajectory/rise is good but dilution is systematically wrong, revisit entrainment rather than buoyancy.
If both trajectory and dilution are wrong, inspect the top-hat/Gaussian conversion and local Froude treatment.

### C. Centerline mapping
Use ordinary stagnant warm cases T01/T03/T06/T08.

Tune `centerline_ratio_asymptote`; CORMIX documentation states that point-source bulk dilution `Sf` is
approximately `1.7 x Sc` for established flow.

### D. Crossflow
Use T09/T10/T11.

Tune `crossflow_entrainment` primarily for dilution and `drag_coefficient` primarily for trajectory.

### E. Hold-back verification
Do not tune against T05, T13-T18 initially.

If those fail systematically, that is evidence of a missing physical mechanism or an applicability boundary,
not automatically a reason to add more fitting parameters.

## 9. What should trigger CORMIX/PLUMES directly

Even if the screen runs, treat these as automatic advanced-analysis triggers:

- strong or reversing tidal currents;
- non-uniform bathymetry or nearby breakwaters/shorelines controlling the plume;
- persistent stratification or pycnocline interaction;
- recirculation / intake interaction;
- plume merging or multiport diffusers;
- dense/brine discharge;
- outlet immediately boundary-attached;
- requirement to rely on far-field dispersion or surface heat loss;
- sensitive ecological receptor or permit-specific mixing-zone geometry.

## 10. Model limitations

Important limitations include:

- integral top-hat approximation;
- simple empirical entrainment closure;
- no waves;
- no tidal history or recirculation;
- no free-surface spreading after impact;
- no Coanda/bottom attachment model;
- no plume-plume interaction;
- no multiport diffuser;
- no atmospheric cooling;
- linear stratification only;
- atmospheric-pressure EOS-80;
- crossflow treatment is engineering-level, not a clone of CorJet;
- centerline conversion is approximate.

This is exactly why the tool is designed to turn AMBER when its assumptions become important.

## 11. Source references

Key references to keep beside the model:

- G.H. Jirka (2004), *Integral Model for Turbulent Buoyant Jets in Unbounded Stratified Flows. Part I: Single Round Jet*, Environmental Fluid Mechanics 4:1-56.
- US EPA (2024), *PLUMES2.0 Dilution Model: Model Theory and User Manual*, EPA/600/B-24/339.
- CORMIX User's Manual and CORMIX1 technical documentation.
- Fischer, List, Koh, Imberger & Brooks, *Mixing in Inland and Coastal Waters*.
- UNESCO / EOS-80 seawater equation of state.

