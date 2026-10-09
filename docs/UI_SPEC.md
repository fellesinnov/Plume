# Plume Design Studio UI specification

**Status:** SPEC-0 UX/product contract. Streamlit is the preferred first UI, but all physics, providers, criteria and persistence contracts remain UI-independent.

## 1. Product experience

The first user-facing application is one coherent **Plume Design Studio** with five stages:

```text
Project → Ocean → Design → Simulate → Results
```

These are views over the same project/config/data contracts, not separate modelling implementations.

The primary workflow is:

1. create/open a named project;
2. choose a site/location and permit criteria;
3. acquire or load an environmental history;
4. inspect that history and pin one representative/adverse timestamp;
5. tune outlet geometry/operation while the plume calculation updates live;
6. save the selected design as a project revision;
7. simulate that locked design over the selected historical period;
8. inspect annual permit metrics, worst cases, plots and animation.

## 2. Project view

A project owns:

- project ID and human-readable name;
- site/location and datum metadata;
- permit criteria;
- selected/locked outfall configuration;
- provider specifications;
- design-basis snapshot provenance;
- revision history;
- simulation run history.

Customer/site projects are local working data and are **not committed to Git by default**.

Default persistence:

```text
workspace/
  projects/
    <project-id>/
      project.yaml
      revisions/
      design/
      runs/
```

`configs/example.yaml` remains a public/demo config. The UI may explicitly export a portable YAML/JSON config when the user wants to share or archive one.

A saved project config contains provider/site specifications and the chosen design, but never credentials. Exact provider cache hashes and run provenance belong in workspace metadata/manifests so the portable config does not depend on one computer's cache path.

## 3. Ocean view

### Site selection

The first Streamlit UI should support both:

- map-based point selection; and
- exact latitude/longitude entry.

The selected coordinate becomes normal project config data.

### Historical window

Default historical period is the **previous complete calendar year** when the provider can supply it.

For example, during 2026 the default is:

```text
2025-01-01 → 2025-12-31
```

The user can change the range/cadence.

### Acquire once, inspect many times

Fetching environmental data is an explicit action such as **Load ocean history**.

The provider cache is keyed by the exact request. Geometry sliders must never re-fetch ocean data.

The Ocean view should show:

- annual temperature history;
- useful depth traces/bands rather than surface temperature alone;
- salinity history where available/relevant;
- current speed/direction history where available;
- data gaps;
- dataset/grid resolution;
- requested versus actually used coordinate;
- wet-cell fallback or depth interpolation/extrapolation warnings.

### Pick the design timestamp

The user can choose a date/time from the annual plot or a synchronized date/time control.

Selecting a timestamp pins a normalized snapshot:

```text
T(z)
S(z)
u(z), v(z)
water depth / surface state where available
provider provenance
```

The UI then shows the full vertical profiles for that instant.

A later feature may rank candidate "adverse" timestamps using permit-relevant severity. Do not define "worst day" as simply the highest surface temperature; stratification, current, depth profile and operating state can matter.

## 4. Design view — live calculation

Design Mode evaluates one pinned environmental snapshot repeatedly using the **same model stack** as historical simulation.

### Controls

Initial supported controls should include:

- flow;
- discharge temperature or process ΔT;
- discharge depth;
- round-port diameter;
- vertical angle;
- azimuth.

The UI contract must remain ready for:

- multiport diffuser: port count, diameter, spacing/layout;
- other qualified outlet adapters such as vertical, horizontal, near-surface or surface discharge.

Unsupported outlet types must be clearly disabled/rejected rather than approximated silently.

### Live recomputation

Changing a design control should:

1. update the normalized candidate config;
2. rerun only the needed plume/field/criteria calculation against the pinned snapshot;
3. update metrics and figures;
4. never perform a network/provider fetch.

Use short debouncing or "while dragging / after release" optimization if needed, but the interaction should feel live. Show calculation status/latency rather than leaving stale figures on screen.

### Primary plume visualization

The supplied mockup defines the visual intent.

The vertical section should display:

- physical **Depth [m]** and **Distance [m]** axes;
- discharge position/direction;
- actual ambient water layers/profile from the pinned data;
- layer labels or an adjacent profile panel with depth, temperature, salinity and useful current information;
- nested plume contours whose colours represent **excess temperature ΔT relative to the local ambient**, not decorative absolute-temperature blobs;
- a stable, labelled heatmap legend;
- clearly emphasized configured permit contour(s), e.g. ΔT = 2 °C;
- surface and bottom boundaries.

The ambient background and plume field carry different meanings: ambient colours/layers describe the receiving water; plume colours encode the thermal increment. They must not be visually ambiguous.

A plan view should complement the section when current/azimuth makes horizontal direction important.

The contour shape must come from the qualified field-reconstruction model/similarity profile. UI code must never manufacture a prettier plume shape than the model predicts.

### Plot-only isotherm preview

Provide a lightweight visual ΔT threshold control (defaulting to the configured isotherm criterion, typically 2 °C). Moving the cyan contour should reuse an already-solved/reconstructed field, update corresponding **sampled-slice** extent indicators, and not refetch ambient data or recompute MODEL-1. This is a **preview of a level set**, not an edit to the locked permit criterion: the two values must be visibly distinguished. Changing a true regulatory criterion is a separate config/versioned revision decision (PERMIT-1). The heatmap colour scale must not shift solely because a display contour changes. The dark outer limit of near-field support is not a zero-excess contour.

### Live metrics

Depending on supported physics/criteria, show compact design metrics such as:

- ΔT threshold plume length;
- max width / area / volume above threshold;
- surface contact and surface hotspot;
- temperature/ΔT at configured receptor or mixing-zone distance;
- neutral/trapping depth;
- relevant permit pass/fail;
- applicability/data warnings.

## 5. Saving a design

**Save design** creates a project revision in the ignored workspace.

A revision records:

- normalized configuration;
- pinned design-basis timestamp and provider provenance;
- model version/commit;
- selected criteria;
- candidate metrics/warnings.

Saving a design does not mutate downloaded ocean data.

The latest explicitly selected revision becomes the project's **locked design** for historical simulation.

Changing controls after the last save makes the UI visibly **unsaved**. Changing a locked configuration after a historical run makes those run results visibly **stale for the current design**; old runs remain preserved.

## 6. Simulate view

The simulation view runs a selected locked revision over an environmental period.

Before running, show a preflight summary:

- project/revision;
- time range/cadence;
- source forcing availability;
- environmental cache coverage;
- criteria;
- model/reference qualification state;
- estimated number of timesteps;
- expected artifact-retention policy.

Historical simulation should reuse the existing provider cache whenever its request coverage is sufficient.

A rerun with changed geometry should require new model results, but **not** a new Copernicus download.

## 7. Results view

Initial annual results should include:

- metric time series;
- worst timestamp(s);
- annual maximum;
- P95 / P99 where meaningful;
- hours/days exceeding each configured criterion;
- longest continuous exceedance;
- selected/relevant receptor results;
- worst-case and representative section/plan frames;
- annual/seasonal plume envelope;
- animation through time.

Every result view should make clear which project revision and environmental dataset/run manifest it represents.

## 8. Cache layers and invalidation

Caching is part of the product, not an afterthought.

### Provider cache

Keyed by the normalized provider request, including dataset/variables, spatial selection, depth selection, time range, cadence/aggregation and provider options.

Changing outlet geometry or permit criteria does **not** invalidate this cache.

### Physics/model cache

Keyed by at least:

- normalized geometry/source/model config;
- normalized environmental snapshot/input hash;
- Plume model version/commit.

Changing render colours or figure layout does not invalidate physics.

### Render cache

Keyed by physics result identity plus rendering options.

This lets figures/animations be restyled without rerunning the solver.

### Annual storage policy

Do not require a full dense 2-D/3-D thermal field for all 8,760 hourly timestamps.

Always retain compact timestep metrics and enough qualified plume state/trajectory to reproduce selected frames. Full spatial fields can be saved at:

- none;
- selected/worst timestamps;
- a configured stride;
- every timestep when explicitly requested.

Animation can render from stored model state or cheap field reconstruction rather than forcing enormous storage.

## 9. Streamlit boundary

Streamlit is the preferred first application shell because it is quick to iterate and matches the proven HeatHandler configurator workflow.

Streamlit may own:

- navigation;
- map/site controls;
- sliders/forms;
- plots;
- progress/status;
- project open/save/export actions.

Streamlit must **not** own:

- plume equations;
- provider-specific science/data normalization;
- cache identity rules;
- config validation;
- criteria calculations;
- result provenance.

Those belong in the headless package so Design Studio, CLI/notebooks, HeatHandler and future services all use the same implementation.

## 10. Credentials

The UI may show only credential status such as **Copernicus configured / not configured**.

It must never display, serialize or log secret values.

Copernicus credentials are loaded from ignored local environment state. They are not required for manual/file-backed Design Mode.

## 11. First implementation slices

The UX should be implemented progressively rather than as a large fake dashboard:

1. project/config persistence + inline/file environmental snapshot;
2. qualified near-field + field reconstruction;
3. fully live Design view;
4. Copernicus annual Ocean view/cache/date selection;
5. historical Simulate view;
6. annual Results/animation;
7. later live probe/SCADA inputs.

No UI placeholder should be mistaken for a physically computed plume.
