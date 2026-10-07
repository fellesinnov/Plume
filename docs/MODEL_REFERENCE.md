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

Use: strong external behavioural/architecture reference. Do not copy/adapt source into Plume unless the human explicitly chooses a GPL-compatible strategy.

### Ebb Carbon Plumes_Public
https://github.com/ebbcarbon/Plumes_Public

Public MIT-licensed Python reimplementation of PLUMES2.0 with extensive executable trace/reference cases and decoded file/physics notes. Its README explicitly states that the upstream executable ships without source and that the port was reconstructed from manuals, literature and executable traces.

Use: potentially very valuable secondary implementation, parser/reference-case research and cross-check. Any direct source adaptation should still be explicit and attributed; independent reference comparisons remain useful even when permissive reuse is possible.

Neither implementation automatically replaces the selected PLUMES2.0 executable as the project's regression source of truth.

## 4. Reference roles

REF-1 must assign explicit roles rather than blend evidence:

- **Primary executable regression:** one selected checked-in PLUMES2.0 binary/version.
- **Secondary executable regression:** the other checked-in PLUMES2.0 release.
- **Independent implementation references:** SFEI Visual Plumes and/or Ebb port where useful.
- **Independent physical evidence:** published experiments/literature/site observations.

Calibration cases and hold-back cases must be separate.

## 5. Golden-reference layout

Derived golden evidence should live outside `References/`, for example:

```text
tests/reference/plumes2/
  <case-id>/
    manifest.json
    input/
    raw/
    normalized.*
```

Each manifest should record:

- case ID/purpose;
- source commit;
- reference distribution and executable path;
- executable SHA-256/version;
- runner/OS identity;
- exact inputs;
- exact raw outputs;
- any GUI choices not represented in files;
- whether the case is calibration or hold-back.

Raw output is evidence; normalized output is derived test material.

## 6. Interpretation

Reference agreement can show that Plume tracks a named implementation for named cases. It does **not** by itself establish physical truth, regulatory acceptance or applicability outside the compared mechanisms/envelope.
