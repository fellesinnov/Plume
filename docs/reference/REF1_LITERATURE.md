# REF-1 literature / physical-evidence ledger

Date: 2026-10-07

This file records the independent physical evidence used to route MODEL-1 qualification. It is not
a substitute for raw experimental data and it does not create a claim of physical validation.

## Evidence principles

- software-to-software agreement is regression evidence, not physical validation;
- a dataset used to select or tune a closure is not later called independent hold-back evidence;
- do not digitize plotted points merely to manufacture a golden case;
- preserve the published variable/dilution definition before comparing numbers;
- keep centreline, flux-average and minimum/surface dilution distinct.

## Fan (1967)

**Fan, L.-N. (1967), _Turbulent Buoyant Jets into Stratified or Flowing Ambient Fluids_.**
California Institute of Technology thesis.

Public landing page:
https://thesis.caltech.edu/9290/

Why it matters:

- classic round buoyant-jet experiments underlying later entrainment-model development;
- includes stagnant stratified cases and uniform-crossflow cases;
- reports trajectory, plume width and dilution/concentration observations;
- provides a formulation-oriented evidence family that predates PLUMES/Visual Plumes.

Project role:

**MODEL-1 formulation/calibration set.** Use selected clean Fan cases to discriminate the
UM3-reference entrainment closure from a literal/published projected-area formulation and to freeze
any coefficient that genuinely requires calibration.

The EPA Visual Plumes manual also distributes/quotes a Fan Run 16 verification example and an
ASCII verification-file format. That case is useful for trajectory/width regression but is a
stagnant stratified case, not by itself the cross-current closure discriminator.

EPA Visual Plumes text:
https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P1001G6B.TXT

## Lee & Cheung (1991)

**Lee, J.H.W. and Cheung, V. (1991), _Mixing of buoyancy-dominated jets in a weak current_.**
Proceedings of the Institution of Civil Engineers, Part 2, 91, 113-129.

Public research-record page:
https://researchportal.hkust.edu.hk/en/publications/mixing-of-buoyancy-dominated-jets-in-a-weak-current/

Why it matters especially for Plume:

- vertical **heated** jets in crossflow;
- explicitly buoyancy-dominated regimes and weak-current transition behaviour;
- detailed concentration measurements and flow visualization;
- 48 laboratory experiments / 107 reported data observations are described in later analyses.

Project role:

**Primary MODEL-1 physical hold-back family.** Do not use Lee-Cheung observations to tune a
coefficient or select between closures and then cite them as verification.

## Seckin et al. (2026)

**Seckin, G. et al. (2026), _Comparison of 3D methods for estimating initial dilution of single
port vertical jet discharges_.** Dynamics of Atmospheres and Oceans 114, 101662.

DOI:
https://doi.org/10.1016/j.dynatmoce.2026.101662

Why it matters:

- evaluates UM3 and DKHW against two independent experimental families;
- reports 99 mostly momentum-dominated Fan observations and 107 buoyancy-dominated Lee-Cheung
  observations;
- reports stronger UM3 agreement on the Fan set and increased error/reduced agreement on the
  Lee-Cheung set.

Project interpretation:

This is independent support for using the more product-relevant Lee-Cheung family as the hard
hold-back rather than tuning until UM3 parity looks good.

## Seckin, Ersu & Macit (2025)

**_New formulas for estimating initial dilution of buoyancy-dominated jets in a current_.**
Dynamics of Atmospheres and Oceans 110, 101561.

DOI:
https://doi.org/10.1016/j.dynatmoce.2025.101561

Useful published context:

- restates the Lee-Cheung BDNF/BDFF asymptotic dilution relations;
- discusses the Huang et al. and Mukhtasor et al. transition formulations;
- notes the long-standing concern that ambient current can materially affect weak-current
  buoyancy-dominated dilution;
- reports that earlier analysis excluded five observations and questioned part of the original
  Lee-Cheung table without proving a recording error.

Project interpretation:

Do **not** silently delete inconvenient Lee-Cheung observations. Any exclusion in MODEL-1 must have
a predeclared physical/data-quality reason and must be reported both with and without the disputed
points where feasible.

## TEOS-10 / GSW

Official TEOS-10:
https://www.teos-10.org/

Official GSW-Python:
https://github.com/TEOS-10/GSW-Python

Project role:

Production thermodynamic reference. TEOS-10 supersedes EOS-80 and uses Absolute Salinity and
Conservative Temperature/potential enthalpy. Plume will target TEOS-10 for customer-facing thermal
physics; old Knudsen/EOS-80 paths remain reference-compatibility evidence only.

## Physical-evidence handoff to MODEL-1

MODEL-1 owes a deterministic qualification notebook/script or test harness that:

1. runs the same Plume kernel/closure interface against selected Fan formulation cases;
2. freezes the chosen closure/coefficient set;
3. only then opens the reserved Lee-Cheung hold-back;
4. reports trajectory/rise, width where available, and the correctly matched dilution definition;
5. reports all exclusions and provenance;
6. derives tolerances from the resulting error distribution instead of inventing them first.

Until raw numerical observations with clear provenance are available, these literature families are
qualified targets, not synthetic numeric goldens.
