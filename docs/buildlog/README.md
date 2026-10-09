# Current build / evidence status

## TIME-1A historical data foundation — 2026-10-09 (source candidate)

**SCOPE:** normalized time/depth scalar and ENU-current CSV providers, whole-second UTC timestamp selection with explicit missing slots, SHA-bound reusable workspace cache, preserved time-varying plant providers and optional depth-current MODEL-1 bridge, all headless. Branch `time-1a-historical-foundation` cut from verified `main` **`750e94ecc1ad487e30e672cf8879a4ca868c4364`**. **Bounded isolated sandbox evidence:** 20/20 focused tests PASS, including subsecond sample anti-aliasing, missing-hour/no-interpolation, corrupted-cache and CSV-input-change discriminators, no-provider-reload after acquisition, original source CSV retained, legacy static snapshots, project CSV path rebasing and strict current-shear export guard, and 8,760 hourly synthetic static forcing pins; source compile PASS. These checks use local **config/provider/workspace contract stubs** because the sandbox lacks complete GitHub checkout, official GSW and Streamlit; **do not promote to full integration**. Synthetic 14-day temperature/current input heatmap created in ignored sandbox workspace (335/336 valid hourly columns, one explicit gap). **HOLD** for complete exact-head install/regression suite and optional official-GSW model seam. No Actions run, no merge, no credential use, `References/` unchanged. See [TIME-1A source evidence](2026-10-09-time-1a.md) and [API contract](../TIME_1A.md).


## DESIGN-1 IMPLEMENTATION INTEGRATED — 2026-10-09

**Human-authorised squash merge:** [PR #10](https://github.com/fellesinnov/Plume/pull/10) from `design-1-live-studio`, exact final source head `d1bbd4cb3d1b9c1a9fa8646807be01d6e28baf70`, base `main` `a95806fd0738d990a56ddd37571cfab38d9f7f5f`, confirmed merge SHA **`184156f00350803621a171107e6271f7c8b9dbcc`**. The user-observed Windows full suite finished **87/87 passed, 0 failed, 1 expected warning, 7.42 s** (six CRLF-expanded local text worktree files; the originally pinned Git SHA/size are proved by read-only in-memory reconstruction; do NOT claim local raw-byte fidelity). Actual Streamlit/GSW Project/Ocean(local)/Design, model-derived section/plan, fast preview cyan ΔT level, comparison/save/export were human-observed in the prior laptop smokes. **Local `git rev-parse HEAD` was not pasted:** user-run source-version evidence is not independently exact-head certified; accepted by explicit maintainer integration decision. No Actions run. All 52 immutable `References/` Git blobs and manual-only workflow blob were verified unchanged across integration. **Physical `MODEL-CLOSURE-1` and `FIELD-PROFILE-1` OPEN, `MODEL-TOL-1` BLOCKED**; no permitting proof or model physical validation. **Next seam: `TIME-1`**. [Exact close record](2026-10-09-design-1-integrated.md).


## DESIGN-1 Windows reference-identity harness convergence — 2026-10-09

**Source convergence only; exact-head full Windows test still OWED.** The user reports **80 pass / 1 fail** after the live Streamlit preview and responsive UI fixes. The sole failure is the same Windows CRLF worktree reference size mismatch (6890 vs original Git 6746). DESIGN-1-WIN-REFQA now checks exact **original Git blob size and SHA**, allowing only a proven read-only *in-memory* reversal of checkout-only CRLF for known text fixtures on Windows and issuing an explicit warning that working copies are not raw byte-exact. Mutated data still fail; executables remain strict. Bounded sandbox **6/6 focused tests PASS**, exact-sized 6746/6890 synthetic discriminator PASS, source compilation PASS. Full suite on exact new PR head and narrow Studio smoke remain **OWED**. `References/` and Actions workflow unchanged; physical gates OPEN. [Detailed log](2026-10-09-design-1-windows-reference-qa.md).


## DESIGN-1 second Windows check — 2026-10-09

**User-observed:** `compileall` succeeded and `pytest` reported **79 PASS / 1 FAIL** after the fast cyan ΔT contour preview was added; the sole reference-manifest byte mismatch remained 6890 vs 6746 in the *existing Windows worktree*. We reproduced that attributes do **not** retrospectively rewrite existing CRLF working files and that bounded `git restore --source=HEAD --worktree -- <specific reference>` restores the original LF bytes when `References/** -text` is active. The contour works quickly; screenshot reveals narrow viewport metric truncation/combined figure title overlap, so a source-only presentation fix and Agg layout regression are proposed. Two incidental user commits added only `src/*.egg-info` install metadata, cleaned from branch and ignored. Exact laptop `git rev-parse HEAD` was not supplied. Full green exact-head suite and responsive screenshot **OWED**; **mechanical HOLD**. See [laptop feedback](2026-10-09-design-1-laptop-feedback.md).


## DESIGN-1 laptop feedback and Windows reference-byte root cause — 2026-10-09

**Source candidate / integration HOLD.** User-observed Streamlit Windows session produced live computed section/plan plots, comparison, save/lock and two YAML exports. The user-reported full suite was **77 pass / 1 fail**; sole failure: Windows worktree `Example_project.prj` is 6,890 B versus 6,746 B pinned blob. Exact source Git blob independently confirms 144 LF and zero CR, explaining the +144-byte CRLF conversion. Root `.gitattributes` now protects `References/** -text` on fresh checkout, **without modifying reference evidence**. A new display-only cyan isotherm threshold and cached-slice sampled radius are source-authored, with exact-blob sandbox compile/helper checks, but **not Windows-retested on the new branch head**. Await exact-SHA full green checkout + preview/reopen walkthrough. Physical qualification still OPEN/BLOCKED. See [2026-10-09 laptop feedback](2026-10-09-design-1-laptop-feedback.md).


## DESIGN-1-EXEC source convergence — 2026-10-09

[Execution/evidence record](2026-10-09-design-1-exec.md): PR #10 now includes config-integrity and workspace-scoped session repairs, both with red-before/green-after focused discriminators. Isolated authored-source compilation PASS; 1/1 standalone UI reset test PASS; actual snapshot/provider/project source smoke PASS only with deliberately injected contract stubs. **Full exact-head checkout, real GSW MODEL-1/FIELD-1 evaluation and interactive Streamlit run remain UNPROVEN; integration HOLD.** A new prospective full-GSW two-variant/no-provider-refetch and computed-PNG regression is authored and syntax-checked, **not executed**. No Actions dispatch, reference edits or merge. Model physical gates remain OPEN/BLOCKED.


## DESIGN-1 local pinned-snapshot Studio candidate — 2026-10-08

Writer branch `design-1-live-studio` cut from `main` `a95806fd0738d990a56ddd37571cfab38d9f7f5f`. Headless pin/evaluate/project-revision code plus a Streamlit Project/Ocean(local)/Design shell is a **SOURCE CANDIDATE**; local standalone `compileall` **PASS**, plus isolated provider/snapshot/project source smokes with contract stubs **PASS** (not full product dependencies). Combined package/official GSW numerical runtime, full `pytest`, exact-provider-no-refetch against real model and interactive Streamlit smoke are **OWED** before integration. Model/field physical qualification (`MODEL-CLOSURE-1`, `FIELD-PROFILE-1`, `MODEL-TOL-1`) remains OPEN/BLOCKED; no permit pass/fail. No Actions run or merge authorised. See [`2026-10-08-design-1.md`](2026-10-08-design-1.md).

## FIELD-1 spatial-field/plots implementation integrated — 2026-10-08

**Human-authorised squash merge:** [PR #9](https://github.com/fellesinnov/Plume/pull/9) from `field-1-spatial-reconstruction` into `main` at **`6160b0e889fc879b050a288a8147d06a2275413a`**, from original main `dc280f6d830b942ee20fa695bcd4672b72e6568e`. The exact final PR head was `b5d1bc5825f34b7a416c970855f0305d0efabe7e`. GitHub confirmed PR #9 merged and `main` at the squash SHA. No automatic Actions dispatch or reference changes were part of merge.

FIELD-1 reconstructs a finite near-field 3-D thermal field from the MODEL-1 trajectory with an EPA-informed bounded 3/2-power cross-plume profile; exposes headless section/plan slices and a separate optional Matplotlib renderer with real computed 2 °C contours and distinct ambient/thermal colour scales. Its model/profile assumptions and provenance limitations are documented in [../reference/FIELD1_PROFILE.md](../reference/FIELD1_PROFILE.md).

**Current verified closure:** Explicitly human-approved [Actions run #37873598483](https://github.com/fellesinnov/Plume/actions/runs/37873598483), test commit `734a864e88cebe40bff3af6483bbb46c922a6d95`, Ubuntu CPython 3.11.17 with **official GSW 3.6.23** and optional Matplotlib: full repository structure PASS; editable install PASS; `compileall` PASS; **69/69 tests PASS, 0 failed/0 skipped** (including live GSW numerical round-trip, MODEL-1 → FIELD-1 integration and all reference/CORE checks); real-solver inline-synthetic section/plan plot and provenance PASS. Artifact `field1-postfix-real-gsw` ID **11590768922** (149,636-byte PNG and JSON) was downloaded and visually inspected, with exact provenance SHA confirmed. The one-run scoped push trigger was immediately restored to its original **manual-only** workflow blob `d4937d653e9fe6a47bcb563d92a23bec5293dd4c`, and exactly one run occurred on this authorisation. The trigger changed only the workflow file relative to the pre-trigger candidate; after restoration, source/test files are unchanged. This retires FIELD-1 **mechanical integration HOLD** and the narrow `MODEL-TEOS-1` production numerical GSW runtime gate. **Integration state: IMPLEMENTATION INTEGRATED with explicit human approval**; the downstream implementation sprint is **DESIGN-1** (pinned snapshot/project config and live design controls). Physical `FIELD-PROFILE-1` and `MODEL-CLOSURE-1` remain **OPEN**, `MODEL-TOL-1` **BLOCKED**; no permit acceptance/physical validation claim.

**Earlier reduced sandbox evidence (pre-closer source):** 15 focused tests PASS, 1 real-GSW test SKIP (package absent), `compileall` PASS. A section/plan demo was generated from a **manufactured illustrative trajectory**, not a MODEL-1/GSW run.

**2026-10-08 approved one-run Actions closer:** [Run #37864313011](https://github.com/fellesinnov/Plume/actions/runs/37864313011) on `580f75be1371c08c931cea9366a5ccb6130c133b` installed **real GSW 3.6.23** and successfully generated, checked and uploaded a real MODEL-1 → GSW → FIELD-1 diagnostic section/plan plot + provenance from one **synthetic inline** design case. The figure (149,636 bytes; artifact `11587103805`) reports final bulk dilution **8.927**, section peak **9.988 °C** and plan-slice peak **6.243 °C**. **The overall workflow FAILED:** `compileall` found a literal backslash/newline syntax defect in the new integration test, so the repository `pytest` suite **did not run**. The source typo was corrected at `dccd0f5f9112068e31e50ba045bd20eab2186788`; sandbox `py_compile` PASS on exactly matching corrected test blob `5f8dbbed4f5bc392fd32d21a7a3f3f9ad6535d33`. **No rerun** was requested. The workflow was restored immediately to its original manual-only blob (`d4937d653e9fe6a47bcb563d92a23bec5293dd4c`), and the approved run count remained one.

**Earlier first-run status (now superseded by the successful run above):** the first approved Actions run failed at compileall because of an escaped newline, despite passing the real solver/GSW plot diagnostic. The corrected source then passed the **second, separately human-approved** Actions run with all 69 tests. Physical gate debt remains open, and no `References/` changes, credentials or unapproved Actions occurred during test closure. The subsequent explicitly authorised PR #9 merge is recorded above; human retains merge authority for future changes. See [2026-10-08-field-1.md](2026-10-08-field-1.md).

Detailed sprint record: [2026-10-08-field-1.md](2026-10-08-field-1.md).

---

## MODEL-1 implementation integrated — 2026-10-08

**Merged branch:** `model-1-single-port-kernel`.

**Merged PR:** #7.

**Integrated on `main`:** `1d92bae1b2e1e2bf310a67646f73cfb86042e133`.

MODEL-1 now has an integrated single-round-port Lagrangian near-field implementation baseline adapted from
the pinned MIT Ebb Carbon architecture, with explicit ENU coordinates, conserved mass/vector
momentum/Absolute Salinity/Conservative Temperature, depth-varying horizontal current, a
GSW-backed TEOS-10 production boundary, explicit boundary/oscillation events, and both
`UM3_REFERENCE` and published projected-area current-entrainment candidates behind one internal
qualification seam.

Focused sandbox evidence on the exact source/test blobs now on the branch:

- MODEL-1 focused tests: **27 / 27 PASS**;
- `compileall` over the reduced MODEL-1 sandbox copy: PASS;
- editable install with `--no-deps --no-build-isolation`: PASS;
- Ebb case18/`test23` selected early-jet dilution MARE **0.242 %**, max **0.307 %**;
- Ebb case19/`test28` at 0.01 m/s selected dilution MARE **0.268 %**, max **0.349 %**;
- explicitly approved GitHub Actions run #6 on `0c18ca94d0ab93d944d996a7e970dcef2b784ea0`: **51 / 51 PASS** on CPython 3.11.17 / Ubuntu 24.04 with `gsw 3.6.23` installed.

The tested source/test blob identities were re-read from the remote branch and exactly match the
sandbox candidate. The approved Actions run then exercised the **combined repository** in a full
checkout: structure check PASS, editable install PASS, `compileall` PASS, and **51 / 51 tests PASS**.
That run installed `gsw 3.6.23`, and the existing boundary test imported/constructed the real
`GswThermodynamics` successfully. However, the current real-package test does not yet execute
`p_from_z`, `SA_from_SP`, `CT_from_t`, `rho`, and `t_from_CT` numerically against the installed
package, so `MODEL-TEOS-1` was still open **at the time of MODEL-1 integration**; the later FIELD-1 approved 69-test run above closed this numeric runtime gate.

**Integration state:** **IMPLEMENTATION INTEGRATED / PHYSICAL QUALIFICATION OPEN.** PR #7 was
explicitly authorised and squash-merged to `main` at `1d92bae1b2e1e2bf310a67646f73cfb86042e133`.
This integration does **not** retire `MODEL-CLOSURE-1`: clean numerical Fan formulation/calibration
observations and the untouched Lee-Cheung hold-back are still owed, so no production closure or
physical acceptance tolerance is frozen. `MODEL-TOL-1` remains blocked, and `MODEL-TEOS-1` was open
at that earlier MODEL-1 integration point, before FIELD-1's real-GSW numerical closure. Downstream development may proceed while preserving
that qualification state explicitly in results/provenance.

Detailed record: [2026-10-07-model-1.md](2026-10-07-model-1.md).

**Next seam:** `FIELD-1` — spatial ΔT reconstruction and primary plots.

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
- sandbox **20/20 focused tests PASS**;
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
