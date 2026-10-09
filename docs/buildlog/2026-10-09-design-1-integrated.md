# DESIGN-1 — human-authorised implementation integration — 2026-10-09

## Decision and immutable identity

- **Outcome:** DESIGN-1 **IMPLEMENTATION INTEGRATED**, with explicit human authorisation ("Seems good, merge if u like!") after their completed Windows check. This is **not** physical or permitting validation.
- **PR:** [#10](https://github.com/fellesinnov/Plume/pull/10), `design-1-live-studio`, GitHub-verified final head `d1bbd4cb3d1b9c1a9fa8646807be01d6e28baf70`; base `main` `a95806fd0738d990a56ddd37571cfab38d9f7f5f`.
- **Method:** explicitly authorised squash merge; GitHub returned `merged=true` and merge SHA `184156f00350803621a171107e6271f7c8b9dbcc`. The resulting `main` ref and PR merged state were independently re-read and verified.
- **Writer / authority:** ChatGPT+GitHub held the final writer lease; human explicitly authorised integration. No GitHub Actions runs were dispatched or enabled; workflow blob remains `d4937d653e9fe6a47bcb563d92a23bec5293dd4c`.
- **References:** all **52** files under immutable `References/` have exactly unchanged Git blob IDs across base and merged `main`. No source files, project fixtures, or lock manifests under `References/` were changed.
- **Reasoning:** High — SHA/evidence precision, normalized core/headless contracts, immutable reference identities, qualification warning; Medium — responsive Streamlit UX.

## Actual observed verification

The user exercised a real installed Windows travel-PC venv in VS Code (PowerShell), with official GSW required by the suite and visible interactive Streamlit Design Studio:

- **Final user-reported:** `python -m pytest -q`: **87 passed, 0 failed, 1 warning in 7.42s**, with no skipped tests printed. The warning explicitly identified **six local Windows CRLF-converted text worktree copies**, including the EPA `Example_project.prj`: canonical Git blob **6746 bytes** with LF, local checkout **6890 bytes** due to 144 extra CRs. Revised test checks both original pinned Git SHA and size by **read-only in-memory** EOL reversal; it does **not** claim local worktree bytes are original. Existing executable identities remain byte-strict.
- **Earlier user-observed GUI:** create named project; pin local Ocean T/SP/current; vary supported single-port geometry, flow and temperature; compute actual model-derived section/plan; compare candidates; lock/save a revision; export provider-based and self-contained pinned YAML. User then adjusted the cyan ΔT preview successfully with quick render-only changes and confirmed the UI worked. The preview is deliberately **not** an edit to the saved permit criterion.
- **Source discriminators authored:** project revision mutable-configuration SHA guard; workspace-scoped UI pin/cache; deterministic provider-no-refetch test; real-GSW two-variant MODEL→FIELD PNG discriminator; plot and compact-layout tests; six focused binary-safe reference identity tests. Prior reduced sandbox source checks and exact SHA blob matches are in the preceding buildlogs.
- **Important evidence limit:** The user did **not** paste `git rev-parse HEAD` from their local checkout or Python/GSW versions. Consequently the 87/87 run is **user-observed full-suite evidence associated with the current branch by observed functionality/new-test/warning content**, **not** an independently certified exact-local-SHA log. We retain this narrow provenance debt; the maintainer nevertheless explicitly authorised implementation integration on the available evidence. No official independent Actions closure is claimed.
- **Screen resolution:** The initial narrow-view screenshot found metric truncation/title overlap; source layout fix and Agg overlap test landed before the last 87-test run, but an exact final narrow-viewport screenshot was not submitted. This is a non-physical UX follow-up rather than a reason to undo the authorised merge.

## Integrated product scope

- Headless reusable `plume.design` snapshot/evaluation/project boundary; preserved schema-v1 config, provider request + data provenance, physical SI/TEOS-10 conversion, ENU geometry and depth-positive-down.
- Streamlit **Project → Ocean (local snapshot) → Design** shell with real single-round-port MODEL-1 + FIELD-1 fields, section/plan renderer, metrics marked **UNVALIDATED**, quick adjustable *preview* contour, candidate comparison, persisted ignored-workspace revisions and exports.
- No network Copernicus, map/history acquisition, annual time runner, multiport/far-field, receptor pass/fail, or claims that reference agreement proves environmental compliance.

## Open gates and next actor

**DESIGN-1 implementation is integrated; physical qualification remains separate and OPEN/BLOCKED:** `MODEL-CLOSURE-1` (Fan formulation/calibration versus untouched Lee–Cheung hold-back), `FIELD-PROFILE-1` (independent off-axis thermal/near-source evidence), `MODEL-TOL-1` (blocked on frozen closure). A future strict byte-for-byte local reference experiment must use an original Git checkout rather than the warned six CRLF working copies.

**Next product seam:** `TIME-1` — cached Copernicus/time-history Ocean view, selected profile/date and quasi-steady historical runner via normalized providers. Must deliberately handle original time-varying plant source-provider rebinding after a DESIGN-1 locked constant operating point, never forge annual results from one-hour snapshots.

**Final disposition:** merge verified. New work should start a separate decision-coherent sprint and separate writer lease; no further laptop action required for DESIGN-1 implementation acceptance.
