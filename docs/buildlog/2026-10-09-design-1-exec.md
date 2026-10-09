# DESIGN-1-EXEC — bounded sandbox mechanical convergence — 2026-10-09 (UTC)

## Sprint contract

- **Starting verified remote branch:** `design-1-live-studio` / PR #10 at `918c0344154672cd058ee1ab57e9ac339c9e8ecc`; base `main` `a95806fd0738d990a56ddd37571cfab38d9f7f5f`.
- **Scope:** verify the authored DESIGN-1 candidate on actual source rather than the checklist, execute the strongest sandbox tests available, repair source-provable state/provenance flaws, and route runtime evidence debt. Single writer ChatGPT/GitHub; no merge authority.
- **Retirement evidence:** exact-head full repository installation and compilation, complete design + existing regression suite, official numerical GSW MODEL-1 → FIELD-1 evaluation with two geometry variants/no provider refetch, Streamlit session smoke including save/reopen/plot inspection. Those full-runtime gates are **NOT RETIRED** here.
- **Reasoning level:** High for mutable config provenance, pinned snapshot identity and provider isolation; Medium for Streamlit session state and test mechanics.
- **Out of scope:** physics or radial-profile retuning, Copernicus, annual runner/criteria verdicts, new outlet types, third-party reference imports, Actions dispatch or merging.

## Verified source / sandbox conditions

- The prior DESIGN-1 authored source bundle was available to the ChatGPT sandbox, but a complete Plume repository checkout was **not**. Eight of its nine authored file blobs matched the remote PR-head tree exactly; the ninth was an older copy of this sprint's buildlog (not used for testing).
- Independent remote inspection covered `AGENTS.md` and the required owner reading order, actual DESIGN-1 code, implementation interfaces, existing focused tests, the PR, and remote source/tree identities.
- Sandbox Python **3.13.5**, NumPy/SciPy/Matplotlib/PyYAML and pytest available. Official `gsw` and Streamlit **not installed**. GitHub DNS resolution failed from the sandbox; a bounded `pip install gsw` returned no retrievable distributions. The connector did not provide a complete checkout into the execution runtime.
- Compiling the authored DESIGN-1 Python source using `python -m compileall -q`: **PASS**. This excludes omitted base-repository files, so is not a full-repo compile result.
- `python -m pytest -q tests/design/test_ui_state.py` on the extracted/edited candidate: **1 passed** (the actual reset function is executed from its AST without importing the missing Streamlit dependency).
- The actual `CsvDepthProfileProvider`, `PinnedSnapshot`/pin routine and `ProjectStore`/exports were exercised in an **isolated** source harness using deliberately injected **config/provider/evaluation contract stubs**: PASS for valid/invalid ordered CSV, SHA-256 data digest, provider count, snapshot identity/mutation, project save/reopen, pinned export and config-integrity rejection. This harness is not the full config/model/provider integration suite, and its success must not be promoted to one.

## Independent defects found, changed, and discriminated

1. **P1 post-evaluation mutation:** a frozen `DesignEvaluation` still contains mutable nested `normalized_config`. A caller could alter geometry after calculation but before save, causing revision metrics/provenance to describe another candidate. `ProjectStore.save_revision` now recomputes the canonical config SHA and rejects mismatch **before** creating the revision directory. Added `test_evaluation_config_mutation_is_rejected_before_any_revision_is_written`.
2. **P1 cross-workspace session bleed:** project ID alone was not a sufficient session-scope key. Switching the sidebar workspace while keeping an equal project ID could re-use the previous project's pinned environment and model cache. `_reset_project` now keys session state by resolved workspace root **and** project ID. Added a dependency-free test that executes the actual reset function and checks same-workspace retention / cross-workspace invalidation.

Both mechanisms were run **RED on the original candidate** and **GREEN after correction**, with an isolated integrity discriminator plus the actual one-test UI reset regression. This is meaningful local source evidence, not a Streamlit end-to-end run.

Exact Git blobs of the sandbox-tested corrected artifacts created through GitHub:
- `src/plume/design/projects.py`: `3f974c0f8d63ecf43452474f031a0bbda7d109fe`
- `apps/design_studio.py`: `0c9c4680e7b0f4eee3fbae8b07a001c1dea1d856`
- `tests/design/test_design1.py`: `c2851f59a9a483fd1824e704822ed8a77d974815`
- `tests/design/test_ui_state.py`: `e3d47cf693a0eb5c5b84d67d7656afa4bc7f987e`

## Verdict and evidence debt

**HOLD: source hardening green within the limited sandbox, DESIGN-1 mechanical integration still unproven.** No fresh full `pytest` count is claimed. Official GSW numerical/design evaluation, actual Streamlit interaction and figure inspection, and full checkout reference tests remain owed; earlier FIELD-1 Actions evidence applies to FIELD-1 only.

The bounded next closer requires a complete exact-branch checkout with installed `pip install -e '.[studio]'`, `python -m compileall -q src tests apps tools`, `python -m pytest -q` with no unaccounted skips, two solved design variants with no provider I/O after pinning, and an interactive Streamlit Project → Ocean → Design → save/reopen/export/plot walkthrough. Capture Python/GSW/Streamlit versions, exact source SHA and screenshot or real solved figure. Re-review any repairs against the new head. If unable to establish that environment in the ChatGPT sandbox, the alternate Actions path requires a **separately explicit human authorisation for one named run**; do not auto-trigger.

`MODEL-CLOSURE-1`, `FIELD-PROFILE-1`, and `MODEL-TOL-1` still require independent physical evidence. Numerical software correctness is **not** physical or permitting validation. `References/` and workflow triggers remain untouched; no credential, CI execution or main merge occurred.
