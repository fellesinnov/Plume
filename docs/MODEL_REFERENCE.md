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

## Upstream provenance and source availability

The public upstream repository identified during bootstrap is `uw-ssmc/PLUMES2.0`. Its public `main` currently exposes the same distribution shape as this archive: documentation, example project, licence/disclaimer, icons/images, `plumes2.0v1.exe`, and its manifest. The executable Git blob is the same `dce0fe6b488e233169aec267d0c28706f516d546`.

No FORTRAN source is published in that official repository.

Therefore do not assume that "Fortran-based" means the implementation source can be fetched publicly. If the maintainer later supplies an authentic source distribution that is legally shareable, treat it as a separate provenance/import seam: preserve the files verbatim, record their origin/version/hash, and never silently replace the executable reference with a rebuilt or modified variant.

A third-party reimplementation or decoded specification may be useful research, but it is not the immutable upstream source of truth unless explicitly adopted by a future decision.

## Remote execution boundary

The ChatGPT sandbox used during the 2026-10-07 bootstrap has GNU Fortran 14.2.0 and successfully compiled/executed a small FORTRAN probe.

That proves FORTRAN compiler availability only.

The checked-in reference itself is a Windows executable, and the sandbox does not currently provide Wine. Therefore the exact archived PLUMES executable is a **Windows/local evidence dependency** until either:

1. canonical golden outputs are captured and committed for remote comparison; or
2. an authentic, separately provenance-checked FORTRAN source distribution is intentionally adopted.

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
