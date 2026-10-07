# Backlog

Live queue. A ready item names the observation that retires it.

## SPEC-0 — Define/reset the product
**State:** CANDIDATE on `spec-0-product-reset`.

**Scope:** freeze the old prototype, reset active source, define the digital-twin product/config/workspace contracts, repair the immutable `References/` boundary, and route the first implementation/reference seams.

**Retires when:** the SPEC-0 candidate is integrated to `main` and the active tree no longer implies that the historical screening prototype is the product.

## REF-1 — Qualify the external model references
**Why:** model implementation should start from explicit reference identities rather than experimental prototype coefficients.

**Scope:**
- inventory/hash both checked-in PLUMES2.0 distributions;
- compare the Dec-2025 EPA executable and current UW/SSMC executable on identical canonical cases;
- preserve raw near-/far-field outputs outside `References/`;
- inspect public independent implementations (including SFEI Visual Plumes and Ebb Carbon's PLUMES2.0 port) for reference value, provenance and license;
- choose primary PLUMES regression identity and calibration/hold-back case set.

**Retires when:** canonical cases are reproducible with exact executable/input/output identities and primary-vs-secondary reference roles are documented.

## CORE-0 — Implement package/config/workspace skeleton
**Scope:** create the UI-independent Python package, versioned YAML/JSON config loader/normalizer, workspace/run manifest, provider interface and deterministic constant/inline/CSV providers.

**Retires when:** `configs/example.yaml` loads headlessly, produces a normalized config + manifest in an ignored workspace, and deliberate schema/provider errors fail deterministically.

## MODEL-1 — Qualified single-port near-field kernel
**Scope:** thermal single-port Lagrangian/integral solver with conserved heat/salt, arbitrary ambient T/S profiles, prescribed depth-varying current vector, explicit coordinates and boundary events.

**Retires when:** deterministic conservation/trend tests pass and agreed canonical + hold-back reference cases meet evidence-backed metrics without tuning the hold-backs.

## FIELD-1 — Spatial ΔT reconstruction and primary plots
**Scope:** convert integral plume state into an explicit similarity-profile temperature field; generate section/plan ΔT contours tied mathematically to the model.

**Retires when:** the mockup-style plot is produced from a documented/qualified field reconstruction and deliberate profile/geometry changes cause predictable test failures.

## TIME-1 — Historical digital-twin runner + Copernicus
**Scope:** quasi-steady time runner; provider cache/provenance; Copernicus temperature, salinity and current profiles; annual metrics table.

**Retires when:** a reproducible historical interval can be run from one config with cached provider data and one metric row per forcing timestamp.

## PERMIT-1 — Permit criteria, annual statistics and animation
**Scope:** config-driven ΔT/absolute-temperature criteria, receptor/mixing-zone checks, annual max/P95/P99/exceedance duration, section/plan animation.

**Retires when:** an end-to-end synthetic customer case produces auditable criteria results, summary plots and animation from one config.

## FARFIELD-1 — Prescribed-current far-field decision/implementation
**Scope:** reproduce/understand PLUMES Brooks far-field reference, define state/memory boundary, and document when external hydrodynamics is mandatory.

**Retires when:** selected reference cases are reproduced within agreed metrics and applicability triggers are explicit.

## LIVE-1 — Probe/SCADA provider layer
**Scope:** live/environmental provider adapters using the same normalized forcing contract as historical data.

**Retires when:** a live/mock streaming source can replace historical forcing without changing model/criteria APIs.

## INTEGRATION-1 — Light HeatHandler integration
**Scope:** expose a thin callable/API surface so HeatHandler can construct a Plume config, invoke a run and consume metrics/figures without importing Plume UI code.

**Retires when:** a minimal HeatHandler-side spike calls Plume through the public headless interface with no duplicated plume physics.
