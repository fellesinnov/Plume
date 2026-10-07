# Open gates

Gates hold evidence or judgement that source editing alone cannot settle.

| Gate | Question / evidence owed | State | Retirement evidence |
|---|---|---|---|
| PLUMES-SOURCE-1 | Is authentic public PLUMES2.0 Fortran source available? | **SEARCH CLOSED 2026-10-07 — no public source found** | EPA/SSMC/public-GitHub/web search recorded in `MODEL_REFERENCE.md`; reopen if maintainers publish/provide source |
| PLUMES-REF-1 | Which checked-in PLUMES2.0 executable/version is the near-field regression reference, and are the checked-in outputs coherent? | **CLOSED 2026-10-07 for REF-1** | Exact Git tree/blob identities + byte sizes; effective near-field inputs are identical in the shipped pair; 55/55 normalized near-field rows/events are identical. SSMC-v1 is primary near-field software-regression oracle because the Ebb decode/trace corpus is anchored to it; EPA Dec-2025 is the newer-build sentinel. SHA-256 remains an optional export identity, not an in-repo blocker. |
| MODEL-CLOSURE-1 | Which single-port current-entrainment closure is the physical production default: decoded UM3-reference behavior or a published/physical projected-area variant? | **OPEN — routed from REF-1 to MODEL-1** | Implement candidates behind one kernel interface; use selected Fan cases for formulation/calibration; freeze the choice/coefficients; then evaluate the untouched Lee-Cheung heated buoyancy-dominated hold-back without retuning |
| MODEL-TOL-1 | What near-field metrics/tolerances are defensible? | **BLOCKED on MODEL-CLOSURE-1 / MODEL-1** | Evidence-backed thresholds derived after the closure is frozen, with separate calibration and hold-back error distributions |
| FIELD-PROFILE-1 | Which radial/similarity profile and centerline-to-mean relation should define ΔT contours? | OPEN | Literature/reference-backed choice plus reference cases that discriminate plausible alternatives |
| FARFIELD-SCOPE-1 | Where is the simple prescribed-current far field adequate versus mandatory external hydrodynamics? | BLOCKED on FARFIELD-1 | Reference comparison + documented applicability/trigger criteria |

Do not manufacture tolerances merely to make a gate pass.
