# Current build / evidence status

This file is the single owner for current repository evidence. Historical records may contain old states; they do not override this page.

## Bootstrap qualification boundary — 2026-10-07

**Starting authoritative main:** `ef0be9ac3dc3cb5bcba5f44dd5e37dd724d8b2b3` (`initial commit`).

**Bootstrap branch:** `bootstrap/plume-workflow-v1`.

**Qualified model/source head:** `32a4dda49b9904698e15b5102197c2a93abea6e9`.

**Sandbox-first workflow/policy head:** `5ec49d0465d733861246bd5d029e0c1895b4b02f`.

**Current prototype:** root-level `outfall_screen.py`, `compare_cormix.py`, `self_test.py`, `test_cases.csv`, requirements and example outputs.

**Reference archive:** `PLUMES2.0-main/` is immutable for normal work.

### Integration state

- If this file is being read from authoritative `main`, the bootstrap is **INTEGRATED**, P0-1 is retired, and P0-2 / `PLUMES-REF-1` is the next seam.
- If this file is being read from `bootstrap/plume-workflow-v1`, the candidate is **READY FOR INTEGRATION** and merge authority remains human-only.

### Evidence established

- GitHub repository and implementing prototype inspected.
- Archived reference contents inspected: Windows PLUMES executable, manuals and example project/output are present; no FORTRAN source was found in the checked-in archive.
- ChatGPT sandbox capability probe: GNU Fortran 14.2.0 successfully compiled and ran a minimal FORTRAN program.
- This does **not** prove the archived Windows PLUMES executable runs in the sandbox.
- Earlier bootstrap GitHub Actions verification on model/source head `32a4dda49b9904698e15b5102197c2a93abea6e9`: dependency check, Python syntax, existing `self_test.py`, and 20-case batch smoke **PASS**.
- Batch regression identity at that head: 15 RED / 4 AMBER / 1 GREEN. These classifications are preserved prototype output, not validation evidence.
- Comparison from `32a4dda49b9904698e15b5102197c2a93abea6e9` through `5ec49d0465d733861246bd5d029e0c1895b4b02f` contains only workflow/documentation changes; no Python modelling source changed.
- Sandbox verification of the revised workflow: YAML parse **PASS**; only trigger is `workflow_dispatch`; no automatic `push`, `pull_request`, or scheduled trigger.
- No GitHub Actions run was dispatched for the sandbox-first policy changes.

### Verification policy

- ChatGPT sandbox is the default deterministic closer whenever the required environment can be reproduced there.
- GitHub Actions is manual opt-in only. The human must explicitly approve each run before it is dispatched; do not spend Actions credits merely to duplicate sandbox evidence.
- Local Luna/Windows remains the exception path for exact PLUMES Windows executable/GUI evidence.

### Remaining evidence / debt

- PLUMES Windows golden capture is the next explicit gate/backlog seam (`PLUMES-REF-1` / P0-2).
- No PLUMES regression comparison has been performed yet.
- No claim of physical/model validation is made.
