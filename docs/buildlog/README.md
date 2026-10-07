# Current build / evidence status

This file is the single owner for current repository evidence. Historical records may contain old states; they do not override this page.

## Current boundary — 2026-10-07 bootstrap ready for integration

**Starting authoritative main:** `ef0be9ac3dc3cb5bcba5f44dd5e37dd724d8b2b3` (`initial commit`).

**Candidate branch:** `bootstrap/plume-workflow-v1`.

**Qualified source/workflow head:** `32a4dda49b9904698e15b5102197c2a93abea6e9`.

**Current prototype:** root-level `outfall_screen.py`, `compare_cormix.py`, `self_test.py`, `test_cases.csv`, requirements and example outputs.

**Reference archive:** `PLUMES2.0-main/` is immutable for normal work.

### Evidence established

- GitHub repository and implementing prototype inspected.
- Archived reference contents inspected: Windows PLUMES executable, manuals and example project/output are present; no FORTRAN source was found in the checked-in archive.
- ChatGPT sandbox capability probe: GNU Fortran 14.2.0 successfully compiled and ran a minimal FORTRAN program.
- This does **not** prove the archived Windows PLUMES executable runs in the sandbox.
- GitHub Actions PR run `37585599203` for head `32a4dda49b9904698e15b5102197c2a93abea6e9`: **PASS**.
- Python dependency check, syntax compilation, existing `self_test.py`, and 20-case batch smoke: **PASS**.
- Batch regression identity at that head: 15 RED / 4 AMBER / 1 GREEN. These classifications are preserved prototype output, not validation evidence.
- CI artifact `plume-ci-evidence` ID `11466570616`, digest `sha256:d2d2e3d537fa662b6c38e390d18934800d87762e34ca04c3e3c886a7e58c8d35`.

### Remaining evidence / debt

- The final documentation-only closeout head must retain green PR CI before merge.
- PLUMES Windows golden capture is **not** required to integrate this workflow bootstrap; it is the next explicit gate/backlog seam (`PLUMES-REF-1` / P0-2).
- No PLUMES regression comparison has been performed yet.
- No claim of physical/model validation is made.

## Integration disposition

**READY FOR INTEGRATION** once the final PR check is green. Merge authority remains human-only.
