# Derived reference evidence

This tree contains **Plume-owned derived evidence** for model/reference comparison.

It is deliberately separate from `References/`, which is immutable third-party evidence.
Never copy a normalized file back into `References/` and never edit a raw reference so that a
comparison passes.

## Layout

- `reference-lock.json` pins external repositories and checked-in distribution identities.
- `cases/` contains manifests for named canonical cases.
- `expected/` contains small derived comparison summaries whose provenance is named by the case
  manifests. Large/generated normalized tables should stay out of Git unless a later sprint shows
  they are useful as durable golden material.
- `../reference_harness/` tests the stdlib-only parser/manifest tooling in
  `tools/reference_harness/`.

## Evidence roles

Every case manifest has one role:

- `software_regression` — reproduce/compare a named software implementation;
- `mechanism` — discriminate a particular formulation without being independent validation;
- `calibration` — may be used to select/tune a closure;
- `hold_back` — reserved from tuning and used only after the relevant formulation is frozen.

A case used for calibration does not become hold-back evidence later just because its fit is good.
Reference-software agreement is not physical validation or permitting proof.

## Coordinates and dilution

For PLUMES `ModelResults_TxtOutputs.dat`, the executable labels the vertical result column
`Depth` but prints negative values below the free surface. The REF-1 normalizer therefore records:

- `z_m`: free surface = 0, positive upward;
- `depth_below_surface_m`: positive downward, derived as `-z_m`;
- `dilution_flux_avg`: the executable's `Dilutn (FluxAvg)` value.

Centreline dilution is never silently substituted for flux-average dilution.
