# Run the DESIGN-1 local Design Studio

**State:** DESIGN-1 implementation candidate, not a physically qualified model or permit evaluator.

Install Plume from the repository root with plotting and Streamlit:

```bash
python -m pip install -e '.[studio]'
streamlit run apps/design_studio.py
```

Default local project storage is the gitignored `workspace/`. Override its path with `PLUME_WORKSPACE` or the sidebar. No Copernicus account or network fetch is required.

1. **Project:** create a named project from `configs/example.yaml`, or open an existing workspace project. The portable project config, lock metadata and revisions are written into `workspace/projects/<id>/`. No customer inputs are committed to Git.
2. **Ocean:** choose an explicit UTC timestamp and click **Pin environmental snapshot**. Current local providers are inline temperature/salinity depth profiles, a constant ENU current, and scalar constant or exact-timestamp CSV source forcing. For file-backed static water columns, use `csv_depth_profile` as below. These are snapshots; annual Copernicus history and date ranking come in TIME-1.
3. **Design:** move depth, diameter, vertical angle, azimuth, flow or discharge temperature. Recompute a new candidate against the pinned immutable column with MODEL-1 + FIELD-1, using the same headless call as an eventual historical timestep. Add variants to comparison; **Save & lock design revision** writes the config, snapshot/provenance and metrics, and updates `project.yaml`/lock pointer. Reopening restores the selected pinned snapshot without a provider load. An edited design remains unsaved until explicitly locked.
4. **Simulate/Results:** deliberately non-running shells. TIME-1 and PERMIT-1 will supply their implementations; there are no fabricated historical results.

Static depth-profile CSV example (`water_temperature.csv`):

```csv
depth_m,value
0,12.5
10,10.2
25,8.7
```

The corresponding schema-v1 forcing descriptor, relative to the config file, is:

```yaml
temperature_profile_C:
  provider: csv_depth_profile
  path: water_temperature.csv
  depth_column: depth_m
  value_column: value
```

The CSV provider reads and hashes the exact file bytes, checks finite strictly increasing depth rows and never changes the source. Design snapshot pinning additionally requires explicit 0 m and site-bottom levels in both temperature and salinity columns. Temperature values mean in-situ ITS-90; salinity values mean Practical Salinity. A source `delta_T_C` is relative to local ambient at discharge depth, not surface water.

Exports: A **provider-based locked YAML** is self-contained for inline/constant sources. Configs with CSV file dependencies require companion files and deliberately cannot claim portable self-containment. A **one-hour pinned snapshot YAML** inlines the selected normalized profile and source values for a standalone reproducible design input; it is not the historical forcing source for an annual simulation. Saved workspace revision manifests carry exact provider request/data SHA and model-version/gate notices.

**Warning:** Computed contours are bounded near-field predictions from a provisional reference-formulated cross-plume profile. Displayed threshold reach and area represent a grid-sampled plane only. They do **not** demonstrate regulatory pass/fail, model physical validation, surface impact or full 3-D mixing-zone compliance. `MODEL-CLOSURE-1`, `FIELD-PROFILE-1` and `MODEL-TOL-1` remain outstanding as documented in [GATES.md](GATES.md).

**Locked operating-point boundary:** DESIGN-1 locks edited plant flow and discharge temperature as *constant design-case* source descriptors, even when the original pinned source value came from a CSV series. The original provider request and selected value remain in the snapshot evidence; the locked config is **not an annual replay of the original plant time-series**. TIME-1 must explicitly define/rebind time-varying source providers for historical replay instead of silently treating this design-case constant as the full plant history. On reopening, Design controls start from the saved locked operating point, not the pre-edit Ocean sample.

**DESIGN-1-EXEC source guardrails:** revision saving verifies that the normalized candidate config has not been mutated after evaluation; the UI session pin/cache is isolated by both resolved workspace root and project ID. The original candidate fails the new focused discriminators, while the corrected source passes the bounded sandbox checks. The real Streamlit/GSW walkthrough is still owed; see [buildlog](buildlog/2026-10-09-design-1-exec.md).

**Plot-only contour preview (DESIGN-1 laptop feedback):** The cyan line shows excess temperature ΔT above ambient in the chosen section/plan. `Preview cyan contour ΔT [°C]` defaults to the configured `isotherm_extent` (usually 2 °C), but may be changed without rerunning MODEL/FIELD/provider data. The sampled radius updates from the cached thermal field and the heatmap colour scale does not change. This is an **on-screen visualization control**, **not** a change to saved permit criteria or proof of regulatory compliance; comparisons record which preview threshold was shown. The dark near-field support edge is not a zero-temperature-increase contour.

**Windows reference-byte checkout:** `.gitattributes` now marks `References/** -text` so fresh Windows checkouts preserve the byte-identical reference files. Existing clones created with `core.autocrlf=true` may retain already-converted worktree files after `git pull`. Verify a clean `git status --short -- References/` and re-materialize the affected tracked file from `HEAD` (or make a fresh clone) before rerunning the byte-lock tests; never normalize the references or alter their manifests. See [2026-10-09 laptop evidence](buildlog/2026-10-09-design-1-laptop-feedback.md).


**Visual Studio / Windows follow-up:** PowerShell inside Visual Studio works normally. A clone made before `.gitattributes` existed may still contain CRLF-converted working copies of immutable reference inputs. To diagnose the observed `Example_project.prj` mismatch, compare `git check-attr text -- "<path>"` (expected `unset`), `git cat-file -s "HEAD:<path>"` (6746) and the filesystem byte count (old 6890). If the file was not deliberately edited, `git restore --source=HEAD --worktree -- "<path>"` rematerializes its exact original bytes with attributes now in effect. Never rewrite/normalize/commit original references or update the frozen manifest merely to make a Windows test pass.

**Compact Studio figures:** Section/plan plots use extra title/legend spacing when rendered in a narrow Streamlit column; Section and Plan peak values are grouped in two metrics and preview-plan radius is given a separate readable row. All plotting changes are presentation-only and preserve the computed field and its `UNVALIDATED` qualification.

**Windows reference test update (DESIGN-1-WIN-REFQA):** If this travel-PC checkout retains CRLF-expanded text fixtures, the suite now verifies the *original committed Git blob* by read-only in-memory reversal **only if both exact pinned SHA and byte size match**; it prints an explicit warning that your worktree itself is not byte-identical. No need to keep deleting/recloning the reference file merely to obtain a model-suite PASS. Executables are still byte-strict. A truly byte-faithful checkout is still required before using reference files as raw binary evidence; never edit or normalize files under `References/` to silence warnings. See [qualification evidence](buildlog/2026-10-09-design-1-windows-reference-qa.md).
