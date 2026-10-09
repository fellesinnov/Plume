# DESIGN-1-LAPTOP-FEEDBACK — Streamlit/GSW field evidence & contour preview

**Date:** 2026-10-09. **Writer lease:** ChatGPT on `design-1-live-studio`, draft PR #10, no `main` merge. **Reasoning:** High for reference byte integrity, thermal/criterion semantics and regression evidence; Medium for render-only UI ergonomics.

## Scope and retirement

- Record the human's first actual Windows travel-PC Streamlit session and exported configs.
- Repair Windows Git checkout EOL handling **outside** immutable `References/`.
- Add a fast visual isotherm threshold (default from configured `isotherm_extent`) without altering the physics solve, source provider snapshot, saved criteria or color mapping.
- Retire only after the new exact-head Windows checkout reproduces unchanged reference SHA/size, all full-repo tests pass, two previews render from a cached solved result and save/reopen/export remains functional.

## User-supplied runtime observations (not independently executed by ChatGPT)

- Windows PowerShell `C:\git\Plume`, activated venv: **77 passed, 1 failed** on repository `pytest -q`. The user reports real Streamlit Project creation, local Ocean pin, live Design rerenders, two-candidate comparison, save/lock and two YAML exports. Screenshots show a computed section/plan, both thermal/ambient scales and the cyan `ΔT = 2 °C` line.
- Screenshot's *illustrative* model sample: 11.5 m outlet depth, 1.00 m diameter, +15° vertical, 90° azimuth, 4,000 m³/h, +10 °C source delta; UI reported ~8.12 s compute, 10.19 °C section-slice peak, 2.09 °C horizontal plan-slice peak, 15.7 m gridded 2 °C plan radius. Second comparison row used 2.00 m diameter, 0° vertical. Values are model output, not external physical qualification.
- Uploaded `initial_test.yaml` and `initial_test_snapshot.yaml` preserve a locked 2 m / 11.5 m / horizontal / 4,000 m³/h configuration with two schema-v1 criteria at 2 °C. The main export retains 2025-01-01 through 2025-01-07 clock; snapshot export explicitly reduces to one hour. No credentials were present in the inspected user inputs.
- Laptop `git rev-parse HEAD`, exact Python/GSW/Streamlit versions, and explicit reopened-state result were **not provided**, so do not attach the 77/78 result or screenshots to a verified commit identity or claim end-to-end closure for PR head yet. Absence of a skipped-count in the user-reported output is supportive, but not a separate test log of GSW.

## Reproduced root cause of sole reported test failure

- Failing invariant: `CheckedInReferenceTests.test_case_manifests_pin_the_actual_input_and_output_bytes`.
- File: `References/plumes2.0_12_22_2025/PLUMES2.0_12_22_2025/Example Project/Example_project.prj`.
- Manifest pinned Git blob `883e981014aad44e430859c488a9b45424fcb5c5`, byte size **6746**. Independent retrieval of the actual Git blob showed **144 LF** and **zero CR** bytes; standard Windows `core.autocrlf=true` checkout adds 144 CR bytes => **6890** exactly matching laptop failure. This establishes an EOL checkout artefact, **not** a change to the authoritative Git evidence.
- A temporary synthetic Git-repository discriminator reproduced LF→CRLF conversion under Windows-style `core.autocrlf=true` and demonstrated a **new checkout** with root `.gitattributes` pattern `References/** -text` restores exact LF bytes. Existing working trees are **not** automatically rewritten when the attributes file arrives; a clean reclone or explicitly safe rematerialization of tracked worktree files is required.
- **No paths under `References/` or golden manifests were edited, renamed, rehashed or recommitted.** Raw-byte identity test remains strict.

## Visualization decision (preview distinct from permit criteria)

- User asked whether the cyan line is the +2 °C contour: yes. The cyan isotherm denotes local in-situ **excess** temperature relative to ambient; the darker/jagged outer edge marks the finite support of the reconstructed *near-field*, **not** a zero heating contour.
- Added `Preview cyan contour ΔT [°C]`, defaulting to the locked config's `isotherm_extent` threshold; sample-based plan radius is recalculated by headless `sampled_isotherm_indicators` from existing section/plan grids. High thresholds with no samples report **not sampled** rather than permit pass.
- A preview-only change does not invalidate or execute MODEL-1, FIELD-1, ocean providers or the config cache; retains the normalized `criteria` in exported YAML/revisions. Modelled heatmap normalisation depends only on solved field magnitude, not which cyan line is requested. Comparison rows now disclose their preview threshold.
- Saving/changing regulatory criterion itself remains future criteria UX work (PERMIT-1). No validated 3-D mixing-zone metric, physical closure or compliance verdict was introduced.

## Local mechanical evidence on proposed source

- Corrected `src/plume/design/evaluate.py` was reconstructed independently from the pinned source and matched the exact prepared Git blob `5d4e32b4e2a8ba85115c03a02659f36d6814417c`; `compile` and Python 3.11-grammar AST parsing PASS.
- New headless helper executed in an isolated synthetic `FieldSlice` stand-in: matched sampled area/extent, high threshold returns no sampled area/extent, rejects negative/NaN/infinite input; **PASS**, with no model/GSW runtime claimed for this focused check.
- Corrected `apps/design_studio.py` was independently reconstructed from the previously verified remote source, its exact prepared Git blob `d125fb79458e48eab321a129a3d9a05d6a49a143` matched; `compile` and Python 3.11-grammar AST parsing **PASS**.
- Root `.gitattributes` behavior tested using a disposable Git repository under `core.autocrlf=true`: **PASS** for new checkout. Focused pytest tests for sampler monotonicity, solver/provider non-invocation and stable Matplotlib color scale are authored, **NOT EXECUTED** in a full repository on this authoring sandbox.
- All source remains **UNVALIDATED** physically. `MODEL-CLOSURE-1`, `FIELD-PROFILE-1`, `MODEL-TOL-1` remain open/blocked.

## Evidence still owed / handoff

On a refreshed Windows checkout of the **new exact PR SHA**, check `git rev-parse HEAD`; run `python -m pytest -q` and `git status --short -- References/` (must show no tracked reference edits). Inspect the default +2 °C and changed +1 °C preview without refetch/re-solve; verify save/lock and reopen existing design with criterion still +2 °C, and that comparison rows identify contour level. Supply the final command output and a screenshot. No Actions run; no `main` merge without explicit human authorization.

**Recommendation: HOLD** for exact-head complete Windows rerun and reviewer confirmation. This is an implementation/mechanical evidence boundary only, not physical or permitting proof.
