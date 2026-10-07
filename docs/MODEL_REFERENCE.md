# PLUMES2.0 reference contract

## Immutable archive

`PLUMES2.0-main/` is the checked-in upstream/reference distribution. Normal Plume development treats it as immutable.

Observed in the repository at bootstrap:

- `PLUMES2.0-main/plumes2.0v1.exe` — Windows executable, Git blob `dce0fe6b488e233169aec267d0c28706f516d546`;
- two PLUMES2.0 user manuals under `PLUMES2.0-main/Docs/`;
- `PLUMES2.0-main/Example_project/` with input CSV/project data and `ModelResults_TxtOutputs.dat`;
- Simplified BSD licence;
- no FORTRAN source files found in the checked-in archive.

The archive README describes PLUMES2.0 as a Fortran-based UM3 implementation. That does not mean this repository currently contains its FORTRAN source.

## Remote execution boundary

The ChatGPT sandbox used during the 2026-10-07 bootstrap has GNU Fortran 14.2.0 and successfully compiled/executed a small FORTRAN probe.

That proves FORTRAN compiler availability only.

The checked-in reference itself is a Windows executable, and the sandbox does not currently provide Wine. Therefore the exact archived PLUMES executable is a **Windows/local evidence dependency** until either:

1. canonical golden outputs are captured and committed for remote comparison; or
2. a separately provenance-checked upstream FORTRAN source distribution is intentionally adopted.

Do not silently substitute a reimplementation for the archived reference.

## Golden-reference layout

Future captured cases should live outside the archive, for example:

```text
tests/reference/plumes2/
  README.md
  <case-id>/
    manifest.json
    input/
    raw/
      ModelResults_TxtOutputs.dat
    normalized.csv
```

Each manifest should record at least:

- case ID and purpose;
- source commit;
- archived executable path and SHA-256;
- PLUMES version shown by the program, if available;
- Windows/runner identity;
- exact input files;
- exact raw output files;
- who/what performed the run;
- any manual GUI choices not represented in files.

Raw output is evidence; normalized output is derived test material.

## Interpretation

PLUMES2.0 is the regression/reference source of truth selected for this project. Agreement with it can show that the Python model tracks the chosen reference for named cases.

It does **not** by itself establish:

- physical truth;
- regulatory acceptance;
- applicability outside the cases/mechanisms compared;
- equivalence to CORMIX/CFD/site data.

Those require separate evidence.
