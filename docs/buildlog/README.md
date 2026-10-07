# Current build / evidence status

This file is the single owner for current repository status.

## REF-1 active — 2026-10-07

**Authoritative `main` at sprint start:** `20822afe25175a94ba2b7cb91579e4191b7bc52c`.

**Active branch:** `ref-1-reference-bakeoff`.

SPEC-0 is integrated on `main`. The active tree intentionally contains no production plume
implementation yet.

The detailed REF-1 scope, pinned references, preliminary findings, case matrix and retirement
evidence live in [2026-10-07-ref-1.md](2026-10-07-ref-1.md).

### Active objective

Choose an evidence-backed implementation starting point for the single-port thermal near-field
core and establish the reproducible reference harness that MODEL-1 will inherit.

REF-1 is a **reference/model bakeoff**, not physical validation and not a permit claim.

### REF-1A foundation

The first reference-infrastructure seam is implemented on the active branch:

- `tools/reference_harness/` is stdlib-only and deliberately outside the future production
  package;
- `tests/reference/reference-lock.json` pins both checked-in PLUMES distributions and exact Ebb
  / SFEI external commits;
- `tests/reference/cases/` holds explicit canonical-case manifests with evidence roles;
- `tests/reference/expected/` holds small derived golden summaries, never modified raw evidence;
- PLUMES normalization preserves flux-average dilution and makes the awkward vertical convention
  explicit as surface-zero `z_m`, positive upward, plus derived positive-down depth;
- a content-identity helper computes both SHA-256 and Git blob SHA when the binary is locally
  available.

No file under `References/` has been changed.

### Pinned external candidates

- Ebb Carbon `ebbcarbon/Plumes_Public`:
  `9791c80ff94f706603df0ae473667ccdffd359db` — MIT port, leading adaptation candidate.
- SFEI `sfei/Visual-Plumes-Models`:
  `99283a481a84902ab248fcf3b6041b484daa1c1e` — GPL-3.0, preferred independent behavioural oracle.

### Evidence obtained

- both checked-in PLUMES distributions are pinned by repository tree identity, executable Git blob
  identity and byte size;
- executable SHA-256 remains owed because the current sandbox/connector boundary does not expose
  binary repository contents;
- the shipped example inputs share the same CSV blobs, while the two `.prj` files differ in
  far-field option state;
- direct parsing of the actual checked-in raw outputs gives **55 near-field rows in each build,
  exactly identical**, including the terminal row at step 275 and the trapping/merging/surface
  event sequence;
- each shipped example has **21 far-field rows**, but SSMC uses `power_4_3` with a 109.59 m
  wastefield width while the Dec-2025 package uses `constant` with 96.29 m, so the shipped pair
  does not demonstrate a near-field build change;
- Ebb exposes a clean single-port Lagrangian control-volume seam with conserved mass, momentum,
  temperature and salinity plus extensive executable-trace experiments;
- SFEI provides an independent UM3 code path with stratified ambient, entrainment, multiport and
  Brooks far-field behaviour;
- Ebb's profile experiments establish that executable default, manual 3/2-power profile and a
  literature Gaussian must not be conflated.

### Deterministic checks

No GitHub Actions run.

Sandbox prototype of the exact committed harness:

- `python -m unittest discover -s tests/reference_harness -v`: **11 tests, 8 PASS, 3 SKIP**;
- the three skipped tests deliberately require the full checked-in `References/` tree, which is
  not mounted in this sandbox;
- `python -m compileall` over harness + tests: PASS;
- independent GitHub-source parsing of both real `ModelResults_TxtOutputs.dat` files reproduced
  the committed golden summary: 55/55 identical near-field rows, 21/21 non-identical far-field
  rows, `power_4_3` vs `constant`, 109.59 m vs 96.29 m.

The full-repository test is already present and will verify manifest Git blob IDs, executable
Git blob IDs/sizes, optional SHA-256 values and the derived golden whenever a checkout with
`References/` is available.

### Current gates

- `PLUMES-REF-1`: **OPEN, narrowed** — Git identities are pinned and the shipped-output trap is
  understood; exact executable SHA-256, a controlled identical-input build comparison, and final
  primary/secondary regression roles remain owed.
- `MODEL-TOL-1`: **BLOCKED** — REF-1 will not manufacture a tolerance.
- `FIELD-PROFILE-1`: **OPEN** — REF-1 maps the evidence; FIELD-1 owns the choice unless evidence
  is sufficient to retire it cleanly.
- `FARFIELD-SCOPE-1`: **BLOCKED / mapped only in REF-1**.
- multiport/merging is mapped for OUTLET-2 and is not allowed to expand MODEL-1.

### Execution policy

- `References/` remains untouched.
- Derived manifests, normalized cases, parsers and comparison outputs live outside
  `References/`.
- ChatGPT + GitHub is the writer/reviewer path; sandbox is the deterministic closer when runnable.
- Local Windows/Luna is reserved for evidence that truly needs binary/GUI access.
- **No GitHub Actions run has been requested or authorised.**

### Next action

**REF-1B — single-port near-field bakeoff:** compare Ebb and SFEI mechanism/code paths against the
canonical zero-current/current-sweep/trapping evidence, route disagreements explicitly, and prepare
the MODEL-1 reuse/oracle recommendation. The two executable SHA-256 values can be filled when a
binary-capable checkout is available and do not block headless reference analysis.

### Integration state

**HOLD — sprint active.** No merge recommendation exists yet. Merge authority remains human-only.

## Previous integrated checkpoint

SPEC-0 product reset is integrated at the REF-1 starting `main` identity. Its durable record is
[2026-10-07-spec-0.md](2026-10-07-spec-0.md).

Planned product sequence remains **REF-1 → CORE-0 → MODEL-1 → FIELD-1 → DESIGN-1**, with later
time-series/provider/far-field/permit-report seams following their owned gates.
