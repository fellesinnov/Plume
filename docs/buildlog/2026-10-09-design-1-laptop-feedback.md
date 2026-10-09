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


## Second Windows session: adjustable contour and exact reference recovery

**Human observation:** The +1.5 °C cyan contour moved quickly without refiring the expensive physics solve. `python -m compileall -q src tests apps tools` was followed by `python -m pytest -q`: **79 passed, 1 failed, zero skips reported**. The same strict manifest size guard failed for the unchanged EPA `Example_project.prj`, **6890 versus 6746 bytes**. The submitted screenshot shows the Plan and Section metrics update, but the right-hand result column is now narrow enough to truncate a metric value and overlap some Matplotlib figure titles/axis labels. This is a responsive presentation defect, not an excuse to alter physical contours. The user correctly clarified the terminal is PowerShell inside Visual Studio.

**Version limitation:** The local command did not include `git rev-parse HEAD`, so the user-reported 79/80 test result remains evidence for the laptop working copy, **not** formally attached to a verified PR-head identity. The branch subsequently advanced from our previous exact head `4d3dc08fea5f0e0044f4b82178f1252fbce678f4` to `94a944357af25475577957553f9f6a5562d0dc6a` via two user commits; remote comparison showed six newly tracked `src/plume_engine.egg-info/` editable-install metadata files **only**. No physics or UI source was modified by those commits. The cleanup commit preserves the user commits but removes only those generated artifacts from source and adds `*.egg-info/` to `.gitignore` for future installs.

**Windows cause and bounded repair:** The branch already contains `.gitattributes` `References/** -text`. Independently reproduced in a disposable Git repo with Windows-style `core.autocrlf=true`: the old checkout retains CRLF after receiving the attribute file, whereas `git restore --source=HEAD --worktree -- <specific tracked path>` subsequently restores the original LF bytes (17 versus 20 bytes for a three-line miniature). The real pinned manifest case is 144 LF and 144 extra CR bytes on laptop. Bounded PowerShell commands are recorded in the conversation and use the single failed file, never sweeping or rewriting third-party reference evidence. The user must first confirm the reference file has no intentional local edits.

**Responsive UI follow-up:** A narrow Streamlit right column squeezes three `st.metric` cards; change that grouping to two peak-ΔT cards followed by a full-width preview-plan-radius card, preserving the same values, units and warnings. Increase only Matplotlib layout spacing/figure height (not contour shapes/model equations) to make the combined figure legible in a small column, and retain separate labels for heatmap and ambient water. Add a deterministic Agg text-bounding-box test verifying spacing between figure/section titles, section x-label/plan title, and bottom legend/footer. In a synthetic Matplotlib layout-only harness, the new geometry achieves wide separations; full-renderer and real Streamlit recheck on new commit remain **OWED**.

**Status:** Candidate still **mechanical HOLD** until exact-head complete regression PASS, direct 6746-byte recheck, and optional screenshot showing untruncated cards/plots. `References/` is immutable; no Actions, main merge or physical qualification advance.

## Third Windows test: persistent EOL worktree, harness distinction repaired

User reports **80 passed, 1 failed** with the same old 6890-byte CRLF working copy after pulling UI layout fixes, confirming this is persistent checkout provenance rather than a new thermal model failure. Prior recommendations to delete/discard only the file did not yield a byte-faithful worktree. DESIGN-1-WIN-REFQA now verifies the **committed Git object** with strict SHA and size and admits a **read-only, proven** Windows CRLF in-memory reconstruction only for named text fixtures. Emits a warning instead of falsely labelling local working bytes original; arbitrary edits and executable mismatches still fail. `References/` itself remains untouched. Full newest-commit user verification is awaited; see [Windows reference-QA buildlog](2026-10-09-design-1-windows-reference-qa.md).
