# Backlog

Live queue. A ready item names the observation that retires it.

## SPEC-0 — Define/reset the product
**State:** INTEGRATED on `main` at `20822afe25175a94ba2b7cb91579e4191b7bc52c`.

**Scope:** freeze the old prototype, reset active source, define the digital-twin product/config/workspace contracts, repair the immutable `References/` boundary, define extensible outlet geometry and Design Mode, and route the first implementation/reference seams.

**Evidence:** durable record in `docs/buildlog/2026-10-07-spec-0.md`; no Actions run.

**Retired by:** the active tree now defines the digital-twin product and no longer carries the historical screening implementation as current model truth.

## REF-1 — Reference bakeoff and qualification
**State:** INTEGRATED on `main` via PR #3 at `6fce138287b6df3ae24b0e67569f61855251bf12`.

**Why:** model implementation should start from multiple explicit references rather than one legacy executable or experimental prototype coefficients.

**Scope:**
- inventory/hash both checked-in PLUMES2.0 distributions;
- compare representative executable traces where useful;
- inspect/run the MIT Ebb Carbon PLUMES2.0 port and GPL-3.0 SFEI Visual Plumes/UM3 as independent references;
- map model equations, similarity profiles, multiport behaviour, far-field assumptions and known divergences;
- include independent literature/experiment evidence where available;
- define calibration and hold-back case sets;
- recommend which implementation/material to reuse directly, wrap, or keep oracle-only.

**Evidence:** REF-1A added the stdlib reference harness, pinned manifests/locks and an executable shipped-example golden. Actual checked-in outputs reproduce 55/55 identical effective near-field cases while configured far-field laws differ. REF-1B selects Ebb's MIT LCV architecture as the adaptation source, SFEI as oracle, TEOS-10/ENU as production conventions, and routes the physical entrainment choice to MODEL-CLOSURE-1. REF-1C fixes Fan as formulation/calibration evidence and Lee-Cheung heated buoyant jets as untouched hold-back. See `docs/buildlog/README.md` and `docs/reference/`.

**Retires when:** reference roles and canonical cases are explicit, major disagreements are understood/routed, and MODEL-1 has an evidence-backed implementation starting point rather than a guessed closure set.

## CORE-0 — Implement package/config/workspace skeleton
**State:** INTEGRATED on `main` via PR #5 at `c2c5600363241e30442182c01465417149f4fd23`.

**Scope:** create the UI-independent Python package, versioned YAML/JSON config loader/normalizer, outlet-adapter contract, workspace/run manifest, provider interface and deterministic constant/inline/CSV providers.

**Evidence:** schema-v1 YAML/JSON normalization, structural `single_round_port` adapter, `constant`, `constant_vector`, `inline_profile` and scalar-timeseries `csv` providers, headless `plume prepare`, and prepared-run provenance are implemented on the candidate branch. Sandbox: 13/15 focused tests PASS; `compileall` PASS; editable install + CLI prepare smoke PASS with build isolation disabled because the sandbox has no network. Deliberate unsupported outlet/provider/schema mutations fail deterministically. No Actions run.

**Retires when:** `configs/example.yaml` loads headlessly, produces a normalized config + manifest in an ignored workspace, unsupported outlet types fail explicitly, and deliberate schema/provider errors fail deterministically.

**Retired by:** the schema-v1 example now loads headlessly, deterministic provider/outlet/schema errors fail explicitly, and a prepared run writes normalized config plus provenance manifest in the ignored workspace. No plume-physics qualification is implied.

## MODEL-1 — Qualified single-round-port near-field kernel
**State:** IMPLEMENTATION INTEGRATED on `main` via PR #7 at `1d92bae1b2e1e2bf310a67646f73cfb86042e133`; physical qualification is **not retired**.

**Scope:** implement the first outlet adapter and thermal near-field kernel with conserved heat/salt, arbitrary ambient T/S profiles, prescribed depth-varying current vector, explicit coordinates and boundary events. Reuse/adapt proven permissive implementation material where advantageous instead of reinventing equations.

**Evidence:** 27/27 focused MODEL-1 sandbox tests pass; selected Ebb test23/test28 software-reference dilution checks are within the existing named software-reference bar. Explicitly approved Actions run #6 on `0c18ca94d0ab93d944d996a7e970dcef2b784ea0` passed the full checkout/install/compile/**51-test** repository suite with `gsw 3.6.23` installed. Integration was authorised as an implementation baseline only. A narrower numerical real-GSW smoke remains owed, and clean Fan calibration/formulation observations plus the untouched Lee-Cheung hold-back remain the physical retirement evidence. See `docs/buildlog/2026-10-07-model-1.md`.

**Retires when:** deterministic conservation/trend tests pass and agreed calibration + hold-back reference cases meet evidence-backed metrics without tuning the hold-backs.

## FIELD-1 — Spatial ΔT reconstruction and primary plots
**State:** **IMPLEMENTATION INTEGRATED** into `main` by explicit human-authorised squash merge of [PR #9](https://github.com/fellesinnov/Plume/pull/9) on 2026-10-08, merge commit `6160b0e889fc879b050a288a8147d06a2275413a`. **Physical field-profile qualification remains OPEN**.

**Scope:** convert integral plume state into a defined radial near-field thermal field and generate computed, physically situated section/plan ΔT contours.

**Retirement evidence for FIELD-1 implementation:** Human-approved Actions [#37873598483](https://github.com/fellesinnov/Plume/actions/runs/37873598483) on source-identical test commit `734a864e88cebe40bff3af6483bbb46c922a6d95`: complete repository editable install/compile PASS; **69/69 tests PASS, 0 skipped**, including real official GSW 3.6.23 numeric TEOS-10 round-trip and actual MODEL-1 → FIELD-1 solver/3-D reconstruction; real-solver section/plan PNG and provenance generated and independently inspected (artifact `11590768922`). The earlier run #37864313011 had failed a test-file syntax check; its defect was fixed before this passing run. The one-off trigger was restored immediately to manual-only, with no repeat run. Full evidence in `docs/buildlog/2026-10-08-field-1.md`, qualification assumptions in `docs/reference/FIELD1_PROFILE.md`.

**Next work:** `DESIGN-1` for headless design snapshots/live Project/Design UI. FIELD-1 is implementation-integrated; no further merge decision is owed for PR #9. Keep the model-status flag visibly **UNVALIDATED**. `FIELD-PROFILE-1`, `MODEL-CLOSURE-1`, `MODEL-TOL-1` remain separately owed independent physical evidence; no permitting claims.

## DESIGN-1 — Live Design Studio snapshot mode
**State:** SOURCE CANDIDATE on `design-1-live-studio`; standalone code compilation PASS; full pinned-identity GSW/Streamlit runtime checks and exact project roundtrip owed. See `docs/buildlog/2026-10-08-design-1.md`. No integration or physical qualification claim.

**Scope:** implement the Streamlit Project/Design workflow against the headless core: create/open a named project, load/pin an inline/file environmental snapshot, vary supported outlet depth/diameter/angle/azimuth/flow/discharge temperature live, show model-derived section/plan plume plots and permit metrics, preserve revisions in the ignored workspace, and lock the selected design into a normal config.

**Retires when:** one pinned snapshot can compare multiple deterministic geometry variants through the same MODEL/FIELD/criteria stack with no provider refetch, save/reopen project revisions, and export/select the locked configuration for historical simulation.

## TIME-1 — Ocean browser + historical runner + Copernicus
**Scope:** add the Design Studio Ocean view plus quasi-steady time runner: map/coordinate site selection, default previous-complete-year fetch, shared provider cache/provenance, annual T/S/current plots, date/time selection of a cached profile for Design Mode, and annual metrics table. Geometry/config changes must reuse the ocean cache.

**Retires when:** a reproducible historical interval can be run from one config with cached provider data and one metric row per forcing timestamp.

## PERMIT-1 — Simulate/Results views, permit statistics and animation
**Scope:** config-driven ΔT/absolute-temperature criteria, receptor/mixing-zone checks, annual max/P95/P99/exceedance duration, section/plan animation.

**Retires when:** an end-to-end synthetic customer case produces auditable criteria results, summary plots and animation from one config.

## OUTLET-2 — Additional outlet geometries
**Scope:** add multiport diffuser/plume merging first, then consider vertical/surface/near-surface/open-channel outlet types only where the physics and reference evidence are adequate.

**Retires when:** each added outlet type has an explicit config schema, model adapter, reference/hold-back evidence and shared runner/criteria compatibility.

## FARFIELD-1 — Prescribed-current far-field decision/implementation
**Scope:** compare PLUMES/Visual Plumes/Ebb Brooks-style far-field behaviour, define state/memory boundary, and document when external hydrodynamics is mandatory.

**Retires when:** selected reference/physical cases are reproduced within agreed metrics and applicability triggers are explicit.

## LIVE-1 — Probe/SCADA provider layer and field comparison
**Scope:** live/environmental provider adapters using the same normalized forcing contract as historical data, plus controlled comparison to simple permit-relevant measurements such as surface temperature.

**Retires when:** a live/mock streaming source can replace historical forcing without changing model/criteria APIs and measurement residuals can be recorded without conflating calibration and verification.

## INTEGRATION-1 — Light HeatHandler integration
**Scope:** expose a thin callable/API surface so HeatHandler can construct a Plume config, invoke a run and consume metrics/figures without importing Plume UI code.

**Retires when:** a minimal HeatHandler-side spike calls Plume through the public headless interface with no duplicated plume physics.
