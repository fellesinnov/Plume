# Model equations and calibration notes

## Coordinate system

`z=0` is seabed and `z=H` is the water surface.

The outlet plan direction is +x. The source can be inclined vertically. Ambient current may be directed
at any horizontal angle relative to the outlet.

The integration coordinate `s` is centerline path length.

## State variables

The solver integrates:

- centerline position `r = [x,y,z]`;
- volume flux `Q`;
- vector kinematic momentum flux `P = Q V`;
- temperature flux `Q T`;
- salinity flux `Q S`.

For the top-hat plume:

```text
V = P / Q
A = Q / |V|
b = sqrt(A/pi)
```

where `b` is equivalent top-hat radius.

## Scalar mixing and density

Ambient entrainment `dQ` carries local ambient temperature and salinity:

```text
d(QT)/ds = Ta(z) dQ/ds
d(QS)/ds = Sa(z) dQ/ds
```

The plume density is then recalculated using EOS-80.

Reduced gravity:

```text
g' = g (rho_a - rho_j) / rho_a
```

Positive `g'` is buoyant/upward for warm seawater.

## Momentum

Approximate vector momentum equation:

```text
dP/ds =
    Ua dQ/ds
  + [0,0,g' A]
  + crossflow_drag
```

The first term is ambient momentum carried in by entrainment.
The second is buoyancy.
The third is an engineering CorJet-inspired crossflow drag closure.

## Entrainment

The shear term is based on a Jirka/CorJet-style local entrainment coefficient.

Gaussian form:

```text
alpha_g = alpha1 + alpha2 sin(phi) / Fl^2
```

with nominal:

```text
alpha1 = 0.055
alpha2 = 0.6
Fl_min ~= 4.66
```

The implementation uses the component of trajectory aligned with buoyancy and caps the plume limit through
the Froude floor.

A `sqrt(2)` conversion is applied to obtain an approximate top-hat coefficient.

Shear entrainment:

```text
dQ/ds_shear = 2 pi b alpha_top U_relative_axial
```

Crossflow forced entrainment:

```text
dQ/ds_forced = C_cross 2 b U_perp
```

with default `C_cross = 0.5`.

## Centerline dilution

The integral state gives bulk/top-hat dilution:

```text
S_bulk = Q / Q0
```

CORMIX documentation gives, for established point-source flow, approximately:

```text
S_bulk ~= 1.7 S_centerline
```

The model transitions smoothly from ratio 1.0 at the nozzle to the asymptote:

```text
R(s) = 1 + (R_inf - 1) [1 - exp(-s / (N_D D))]
S_centerline = S_bulk / R(s)
```

Default:

```text
R_inf = 1.7
N_D = 8
```

This mapping should be compared directly with CORMIX output.

## Source scales

The model reports:

```text
M0 = Q0 U0
J0 = g'0 Q0
Fr0 = U0 / sqrt(|g'0| D)
LM = M0^(3/4) / |J0|^(1/2)
```

`LM` is the classical jet/plume transition scale.

It is a diagnostic, not by itself a pass/fail criterion.

## What to calibrate

### alpha_scale
First parameter to adjust.

If trajectory is approximately right but dilution rises too slowly/quickly in stagnant cases:
adjust `alpha_scale`.

Suggested calibration bounds in the supplied optimizer: `0.70 - 1.30`.

### centerline_ratio_asymptote
Adjust only after bulk mixing is sensible.

If bulk dilution agrees but centerline dilution is systematically low/high:
adjust `centerline_ratio_asymptote`.

Suggested bounds: `1.2 - 2.2`.

### crossflow_entrainment
Use crossflow cases only.

If stagnant cases are good but crossflow dilution is wrong:
adjust `crossflow_entrainment`.

Suggested bounds: `0.1 - 1.0`.

### drag_coefficient
Primarily affects trajectory bending.

If crossflow trajectory is wrong but dilution is reasonable:
adjust `drag_coefficient`.

Suggested bounds: `0.5 - 2.5`.

## What NOT to calibrate casually

Do not use the following as curve-fitting knobs:

- gravity;
- EOS density;
- source flow/diameter;
- heat conservation;
- salinity conservation;
- process delta-T.

If a systematic mismatch remains after closure calibration, document it as a model limitation.

## Suggested acceptance of the screening model itself

Before using this tool internally for GREEN/AMBER decisions, aim for a hold-back verification set with roughly:

- centerline dilution error within +/-20-30% over the useful near-field range;
- trajectory/rise error small relative to available submergence;
- no systematic unsafe bias in shallow-water or high-buoyancy cases;
- no false GREEN classifications in hold-back CORMIX/PLUMES cases.

The exact tolerances should be agreed by the responsible environmental/hydraulic engineer.

## Calibration vs validation

Matching CORMIX is **model-to-model calibration**, not validation against nature.

A strong qualification path is:

1. reproduce CORMIX/CorJet trends;
2. cross-check against PLUMES2.0/UM3;
3. compare several dimensionless benchmark experiments from the literature;
4. freeze coefficients;
5. document an applicability envelope;
6. only then use GREEN as an internal "no further concept analysis" gate.
