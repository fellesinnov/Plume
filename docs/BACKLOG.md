# Backlog

Live queue. A ready item names the observation that retires it.

## SPEC-0 — Define/reset the product
**State:** READY FOR INTEGRATION on `spec-0-product-reset`.

**Scope:** freeze the old prototype, reset active source, define the digital-twin product/config/workspace contracts, repair the immutable `References/` boundary, define extensible outlet geometry and Design Mode, and route the first implementation/reference seams.

**Evidence:** structural/config/workflow checks recorded in `docs/buildlog/README.md`; no Actions run.

**Retires when:** the SPEC-0 candidate is integrated to `main` and the active tree no longer implies that the historical screening prototype is the product.

## REF-1 — Reference bakeoff and qualification
**Why:** model implementation should start from multiple explicit references rather than one legacy executable or experimental prototype coefficients.

**Scope:**
- inventory/hash both checked-in PLUMES2.0 distributions;
- compare representative executable traces where useful;
- inspect/run the MIT Ebb Carbon PLUMES2.0 port and GPL-3.0 SFEI Visual Plumes/UM3 as independent references;
- map model equations, similarity profiles, multiport behaviour, far-field assumptions and known divergences;
- include independent literature/experiment evidence where available;
- define calibration and hold-back case sets;
- recommend which implementation/material to reuse directly, wrap, or keep oracle-only.

**Retires when:** reference roles and canonical cases are explicit, major disagreements are understood/routed, and MODEL-1 has an evidence-backed implementation starting point rather than a guessed closure set.

## CORE-0 — Implement package/config/workspace skeleton
**Scope:** create the UI-independent Python package, versioned YAML/JSON config loader/normalizer, outlet-adapter contract, workspace/run manifest, provider interface and deterministic constant/inline/CSV providers.

**Retires when:** `configs/example.yaml` loads headlessly, produces a normalized config + manifest in an ignored workspace, unsupported outlet types fail explicitly, and deliberate schema/provider errors fail deterministically.

## MODEL-1 — Qualified single-round-port near-field kernel
**Scope:** implement the first outlet adapter and thermal near-field kernel with conserved heat/salt, arbitrary ambient T/S profiles, prescribed depth-varying current vector, explicit coordinates and boundary events. Reuse/adapt proven permissive implementation material where advantageous instead of reinventing equations.

**Retires when:** deterministic conservation/trend tests pass and agreed calibration + hold-back reference cases meet evidence-backed metrics without tuning the hold-backs.

## FIELD-1 — Spatial ΔT reconstruction and primary plots
**Scope:** convert integral plume state into an explicit similarity-profile temperature field; generate section/plan ΔT contours tied mathematically to the model.

**Retires when:** the mockup-style plot is produced from a documented/qualified field reconstruction and deliberate profile/geometry changes cause predictable test failures.

## DESIGN-1 — Worst/representative snapshot Design Mode
**Scope:** load one normalized water-column/current snapshot and source operating state; rapidly compare supported outlet depth, diameter, vertical angle, azimuth, flow, discharge temperature and later multiport geometry; show permit metrics/plots; save candidate artifacts to ignored workspace and lock the selected design into a normal config.

**Retires when:** one snapshot can be used to compare multiple deterministic geometry variants through the same MODEL/FIELD/criteria stack and export a selected configuration for annual simulation.

## TIME-1 — Historical digital-twin runner + Copernicus
**Scope:** quasi-steady time runner; provider cache/provenance; Copernicus temperature, salinity and current profiles; annual metrics table. Design Mode should be able to select a cached historical timestamp as its snapshot.

**Retires when:** a reproducible historical interval can be run from one config with cached provider data and one metric row per forcing timestamp.

## PERMIT-1 — Permit criteria, annual statistics and animation
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
