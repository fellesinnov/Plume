# Current build / evidence status

This file is the single owner for current repository status.

## CORE-0 integrated — 2026-10-07

**Merged branch:** `core-0-package-config-workspace`.

**Merged PR:** #5.

**Authoritative `main` at sprint start:** `c11ff07e44a10e75c3012b4c86fbc874cc60157c`.

CORE-0 is integrated on `main` at merge commit `c2c5600363241e30442182c01465417149f4fd23`, establishing the headless package/config/provider/workspace foundation. Detailed record: [2026-10-07-core-0.md](2026-10-07-core-0.md).

Integrated evidence:

- schema-v1 YAML/JSON config normalization;
- structural `single_round_port` adapter with explicit unsupported-type failure;
- deterministic local provider contracts/implementations;
- config-relative paths and corrected demo workspace root;
- headless `plume prepare` producing normalized config + provenance manifest;
- sandbox **13/13 focused tests PASS**;
- `compileall` PASS;
- editable package + CLI prepare smoke PASS without build isolation;
- no GitHub Actions run;
- no `References/` changes.

**Integration state:** **INTEGRATED.** CORE-0 does not claim plume physics or thermodynamic qualification.

**Next seam:** `MODEL-1`.

## REF-1 integrated — 2026-10-07

**Authoritative `main` at sprint start:** `20822afe25175a94ba2b7cb91579e4191b7bc52c`.

**Merged branch:** `ref-1-reference-bakeoff`.

**Merged PR:** #3.

REF-1 is integrated on `main` via PR #3 at merge commit `6fce138287b6df3ae24b0e67569f61855251bf12`. It adds reference/qualification infrastructure and decisions only; there is still no production plume implementation.

Detailed records:

- [2026-10-07-ref-1.md](2026-10-07-ref-1.md) — sprint scope/evidence;
- [../reference/REF1_NEARFIELD_BAKEOFF.md](../reference/REF1_NEARFIELD_BAKEOFF.md) — mechanism/reuse decision;
- [../reference/REF1_LITERATURE.md](../reference/REF1_LITERATURE.md) — independent physical-evidence split.

### REF-1 result

REF-1 now provides MODEL-1 with a concrete starting architecture rather than a guessed closure set:

- **adapt Ebb Carbon's MIT single-port Lagrangian-control-volume architecture**, with attribution;
- keep SFEI GPL Visual Plumes as an independent source/behavioural oracle, not copied product code;
- keep checked-in PLUMES executables/traces as frozen software-regression evidence, not physical
  truth;
- preserve mass + vector momentum conservation and explicit salt/heat conservation;
- preserve the source contraction and element-stretching relations independently corroborated by
  Ebb executable experiments and the SFEI implementation;
- use ambient-relative velocity in the current-entrainment treatment;
- retain the decoded `Um3Entrainment` behavior as the **software-reference closure**;
- do **not** promote the legacy single-plume zero-curvature behavior to physical truth merely
  because it matches PLUMES/SFEI;
- route the final physical current-entrainment choice to `MODEL-CLOSURE-1`, using Fan for
  formulation/calibration and untouched Lee-Cheung heated buoyant-jet data as hold-back;
- use adaptive continuous integration and explicit boundary/oscillation events rather than copying
  the GUI executable's step controller;
- use **TEOS-10** thermodynamics for the production path, not the executable's Knudsen relation or
  Ebb's EOS-80 default;
- normalize product/model coordinates to local ENU with navigation azimuth; reference adapters own
  legacy-axis conversion;
- keep similarity-profile reconstruction in FIELD-1, merging in OUTLET-2 and Brooks/far-field work
  in FARFIELD-1.

### REF-1A — deterministic reference foundation

Implemented outside the future product runtime:

- `tools/reference_harness/`: stdlib manifest/parser/comparison/content-identity tooling;
- `tests/reference/reference-lock.json`: checked-in and external exact identities;
- `tests/reference/cases/`: canonical manifests;
- `tests/reference/expected/`: small derived goldens;
- `tests/reference_harness/`: deterministic/discriminator tests.

PLUMES normalization explicitly distinguishes signed `z_m`, positive-down depth and flux-average
dilution rather than inheriting ambiguous reference labels.

No file under `References/` was changed.

### Checked-in PLUMES evidence

The two distributions are pinned by exact Git tree/blob identity and byte size.

Their shipped example CSV inputs are the same. The two project files differ only in far-field
option state relevant to the observed output difference. Parsing the actual raw outputs gives:

- near field: **55 / 55 rows exactly identical**;
- same trap / merge / surface event sequence;
- same terminal row at step 275:
  dilution 169.754, diameter 6.481 m, x/y/z = 7.017 / 2.082 / -2.512 m;
- far field: **21 / 21 rows, non-identical**;
- SSMC: `power_4_3`, wastefield width 109.59 m;
- Dec-2025: `constant`, wastefield width 96.29 m.

`PLUMES-REF-1` is therefore closed for the near-field reference role:

- **SSMC-v1** = primary software-regression oracle because Ebb's rich decode/trace corpus is
  anchored to it;
- **EPA Dec-2025** = newer-build sentinel/secondary comparison.

Neither is a physical-validation hierarchy.

SHA-256 can still be recorded when a binary-capable checkout is convenient, but it duplicates the
already-pinned in-repository byte identity and is not a reason to require a Windows laptop before
integration.

### Independent physical evidence

REF-1 does **not** calibrate a production model.

The physical qualification split is now explicit:

- **Fan (1967)** — formulation/calibration family;
- **Lee & Cheung (1991)** — reserved heated, buoyancy-dominated current hold-back;
- recent independent 2026 UM3/DKHW comparison reports stronger UM3 agreement on the mostly
  momentum-dominated Fan data than on the Lee-Cheung buoyancy-dominated data, reinforcing the
  latter as the harder product-relevant hold-back.

No plotted points have been digitized to manufacture numerical goldens. Raw/tabulated experimental
data with clean provenance are owed by MODEL-1 before `MODEL-CLOSURE-1` and `MODEL-TOL-1`
close.

### Deterministic checks

No GitHub Actions run.

REF-1A sandbox prototype of the committed harness:

- `python -m unittest discover -s tests/reference_harness -v`: **11 total, 8 PASS, 3 SKIP**;
- the three skips require a full checkout containing the binary `References/` tree, unavailable
  in this sandbox;
- `python -m compileall` over harness + tests: PASS;
- independent parsing of actual GitHub raw PLUMES text outputs reproduced the committed golden.

The full-checkout regression is already present and will verify manifest paths, Git blob IDs/sizes,
optional SHA-256 values and the derived golden whenever such a checkout is used.

### Gates after REF-1

- `PLUMES-REF-1`: **CLOSED** for the near-field reference role.
- `MODEL-CLOSURE-1`: **OPEN**, intentionally owned by MODEL-1 physical qualification.
- `MODEL-TOL-1`: **BLOCKED** until closure freeze + hold-back evidence.
- `FIELD-PROFILE-1`: **OPEN**, owned by FIELD-1.
- `FARFIELD-SCOPE-1`: **BLOCKED**, owned by FARFIELD-1.
- multiport/merging remains OUTLET-2.

### Integration state

**INTEGRATED.** PR #3 merged to `main` at `6fce138287b6df3ae24b0e67569f61855251bf12`.

REF-1 established reference roles, architecture and evidence boundaries before implementation without pretending software parity is physical validation.

No Actions run was required or authorised.

**Next seam:** `CORE-0`, then `MODEL-1`.
