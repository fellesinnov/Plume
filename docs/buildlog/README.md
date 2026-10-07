# Current build / evidence status

This file is the single owner for current repository evidence. Historical records may contain old states; they do not override this page.

## Current boundary — 2026-10-07 bootstrap candidate

**Starting authoritative main:** `ef0be9ac3dc3cb5bcba5f44dd5e37dd724d8b2b3` (`initial commit`).

**Candidate branch:** `bootstrap/plume-workflow-v1`.

**Current prototype:** root-level `outfall_screen.py`, `compare_cormix.py`, `self_test.py`, `test_cases.csv`, requirements and example outputs.

**Reference archive:** `PLUMES2.0-main/` is immutable for normal work.

### Evidence established

- GitHub repository and implementing prototype inspected.
- Archived reference contents inspected: Windows PLUMES executable, manuals and example project/output are present; no FORTRAN source was found in the checked-in archive.
- ChatGPT sandbox capability probe: GNU Fortran 14.2.0 successfully compiled and ran a minimal FORTRAN program.
- This does **not** prove the archived Windows PLUMES executable runs in the sandbox.

### Evidence owed before bootstrap integration

- GitHub Actions CI on the exact candidate must pass Python compile/self-test/batch smoke.
- Exact candidate remote head must be verified.
- PLUMES Windows golden capture is **not** required to integrate the workflow bootstrap; it remains the next explicit gate/backlog seam.

No claim of model validation is made.
