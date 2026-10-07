# External model/reference contract

## 1. Immutable boundary

Everything under `References/` is reference evidence and read-only during normal development.

Current PLUMES distributions:

### `References/PLUMES2.0-main/`
Current UW/SSMC-style distribution checked into Plume.

Observed:
- `plumes2.0v1.exe` (Windows AMD64);
- manuals;
- example project/input/output;
- license/disclaimer/resources;
- no Fortran source files.

### `References/plumes2.0_12_22_2025/PLUMES2.0_12_22_2025/`
EPA December-2025 package.

Observed:
- a different `plumes2.0.exe` binary;
- multiple project/input files;
- raw near-/far-field material including `tempnf.utl`, `tempfl.utl`, `summarynf.utl`, `IndpFarfieldCalc.dat`;
- `fort.100`, which is formatted model/project data, **not Fortran source**;
- no `.f`, `.for`, `.f90`, `.f95`, `.f03` or `.f08` source files.

Do not modify either distribution to make comparison easier. Derived parsers, golden cases and normalized data live outside `References/`.

## 2. Public-source search — 2026-10-07

SPEC-0/REF-1 discovery searched:

- US EPA PLUMES2.0 page and manual;
- public SSMC/UW PLUMES2.0 repository/history;
- other visible SSMC/UW repositories;
- broader web/GitHub queries for PLUMES2.0, UM3, FVCOM-plume and Fortran source.

**Outcome:** no authentic public PLUMES2.0 Fortran source distribution was found.

The EPA/SSMC manual states that Lakshitha Premathilake developed/tested the Fortran UM3 implementation and that Walter Frick supplied the older UM3 code written in Pascal which formed the foundation. The manual also identifies FVCOM-plume as a Fortran ancestor containing a UM3-based initial-dilution module.

Useful public links:

- EPA PLUMES2.0: https://www.epa.gov/hydrowq/PLUMES2
- SSMC PLUMES2.0: https://github.com/ssmc-uw/PLUMES2.0
- PNNL FVCOM-plume background: https://www.pnnl.gov/ssm-marine-pollution-outfall-plume-model

The source-search gate is therefore closed as "not publicly found", not as proof that source does not exist privately. Reopen if EPA/PNNL/SSMC publishes or supplies authentic source.

## 3. Additional public implementations discovered

### SFEI Visual-Plumes-Models
https://github.com/sfei/Visual-Plumes-Models

Public Python core for Visual Plumes/UM3, including ambient profiles, UM3 near field, Brooks far field, tidal buildup and timeseries handling.

License observed: **GPL-3.0**.

Project policy: this implementation may be used aggressively as an external executable/behavioural/reference oracle. Direct copying/linking/adaptation into Plume remains a deliberate deployment/license decision so that future customer-installed software remains flexible. Its GPL license is not a reason to avoid running it for model comparison.

### Ebb Carbon Plumes_Public
https://github.com/ebbcarbon/Plumes_Public

Public **MIT-licensed** Python reimplementation of PLUMES2.0 with extensive executable trace/reference cases and decoded file/physics notes. Its README states that upstream ships without source and that the port was reconstructed from manuals, literature and executable traces.

Project policy: review it as a serious candidate implementation source rather than assuming we should independently rebuild UM3. Reuse/adaptation is acceptable with explicit provenance/attribution if its physics, tests and interfaces are suitable.

## 4. Reference strategy — triangulation, not hierarchy

PLUMES2.0 is useful evidence, not sacred truth.

REF-1 should deliberately compare:

- both checked-in PLUMES2.0 executable releases;
- SFEI Visual Plumes/UM3;
- Ebb Carbon's MIT PLUMES2.0 port;
- published governing theory / laboratory or field evidence;
- later, site/probe observations.

Reference disagreements are first-class findings. Do not average them away or force Plume to match a known implementation defect merely for parity.

Roles may differ by mechanism:

- one source may be strongest for near-field trajectory/dilution;
- another for multiport/merging;
- another for similarity profiles/isopleths;
- another for far-field Brooks behaviour;
- independent measurements/literature ultimately matter more for physical accuracy.

The outcome of REF-1 is therefore an evidence-backed implementation plan and benchmark matrix, not the coronation of one "primary truth" executable.

## 5. Calibration and verification

Use separate sets:

- **mechanism/calibration cases** to identify coefficients or choose between formulations;
- **hold-back cases** never used for fitting;
- where site measurements later calibrate a digital twin, reserve independent times/locations/conditions for verification.

A model can match reference software and still be physically wrong. A model can also intentionally differ from a reference when the reference has a documented defect and independent evidence supports the difference.

## 6. Golden/reference evidence layout

Derived evidence should live outside `References/`, for example:

```text
tests/reference/
  plumes2/
  visual_plumes/
  ebb_plumes/
  literature/
```

A case manifest should record:

- case ID/purpose/mechanism;
- source commit;
- reference implementation/version/path;
- executable/source digest where practical;
- runner/environment identity;
- exact inputs;
- exact raw outputs;
- any GUI choices not represented in files;
- calibration vs hold-back role.

Raw output is evidence; normalized output is derived test material.

## 7. Interpretation

Reference agreement can show that Plume tracks a named implementation for named cases. It does **not** by itself establish physical truth, regulatory acceptance or applicability outside the compared mechanisms/envelope.
