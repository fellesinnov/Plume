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
