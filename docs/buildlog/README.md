# Current build / evidence status

This file is the single owner for current repository status.

## REF-1 active — 2026-10-07

**Authoritative `main` at sprint start:** `20822afe25175a94ba2b7cb91579e4191b7bc52c`.

**Active branch:** `ref-1-reference-bakeoff`.

SPEC-0 is integrated on `main`. The active tree intentionally contains no Python plume
implementation yet.

The detailed REF-1 scope, pinned references, preliminary findings, case matrix and retirement
evidence live in [2026-10-07-ref-1.md](2026-10-07-ref-1.md).

### Active objective

Choose an evidence-backed implementation starting point for the single-port thermal near-field
core and establish the reproducible reference harness that MODEL-1 will inherit.

REF-1 is a **reference/model bakeoff**, not physical validation and not a permit claim.

### Pinned external candidates

- Ebb Carbon `ebbcarbon/Plumes_Public`:
  `9791c80ff94f706603df0ae473667ccdffd359db` — MIT port, leading adaptation candidate.
- SFEI `sfei/Visual-Plumes-Models`:
  `99283a481a84902ab248fcf3b6041b484daa1c1e` — GPL-3.0, preferred independent behavioural oracle.

The two checked-in PLUMES distributions remain immutable under `References/`.

### Evidence obtained so far

- both checked-in PLUMES distributions are pinned by repository tree/executable Git identities;
  executable SHA-256 digests are still owed before `PLUMES-REF-1` can close;
- their shipped example CSV inputs are the same;
- the shipped example near-field tables are identical through the plume-surface event;
- their visible shipped-example divergence begins in the far field and is accompanied by different
  far-field diffusivity flags, so this pair does not establish a near-field build difference;
- Ebb exposes a clean single-port Lagrangian control-volume seam with conserved mass, momentum,
  temperature and salinity plus extensive executable-trace experiments;
- SFEI provides an independent UM3 code path with stratified ambient, entrainment, multiport and
  Brooks far-field behaviour;
- Ebb's profile experiments establish that executable default, manual 3/2-power profile and a
  literature Gaussian must not be conflated.

### Current gates

- `PLUMES-REF-1`: **OPEN** — exact SHA-256 plus controlled canonical build comparison owed.
- `MODEL-TOL-1`: **BLOCKED** — REF-1 will not manufacture a tolerance.
- `FIELD-PROFILE-1`: **OPEN** — REF-1 maps the evidence; FIELD-1 owns the choice unless evidence
  is sufficient to retire it cleanly.
- `FARFIELD-SCOPE-1`: **BLOCKED / mapped only in REF-1**.
- multiport/merging is mapped for OUTLET-2 and is not allowed to expand MODEL-1.

### Execution policy

- `References/` remains untouched.
- Derived manifests, normalized cases, parsers and comparison outputs belong outside
  `References/`.
- ChatGPT + GitHub is the writer/reviewer path; sandbox is the deterministic closer when runnable.
- Local Windows/Luna is reserved for evidence that truly needs a new PLUMES GUI/executable run.
- **No GitHub Actions run has been requested or authorised.**

### Next action

**REF-1A — identity + harness foundation:** obtain/record executable SHA-256, define the derived
reference manifest/normalization contract, and establish the minimal canonical case set before any
production model code is adopted.

### Integration state

**HOLD — sprint active.** No merge recommendation exists yet. Merge authority remains human-only.

## Previous integrated checkpoint

SPEC-0 product reset is integrated at the REF-1 starting `main` identity. Its durable record is
[2026-10-07-spec-0.md](2026-10-07-spec-0.md).

Planned product sequence remains **REF-1 → CORE-0 → MODEL-1 → FIELD-1 → DESIGN-1**, with later
time-series/provider/far-field/permit-report seams following their owned gates.
