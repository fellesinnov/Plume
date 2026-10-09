# Plume

**Plume is a permit-oriented thermal-discharge digital twin engine.**

The target is not a one-off screening calculator. A Plume project combines fixed outfall geometry with time-varying plant and ocean conditions, predicts the excess-temperature plume, derives permit-relevant metrics, and produces useful plots/animations through time.

## Product target

Plume is being designed to support:

- single submerged warm-water outlets first, with room for multiport geometry later;
- time-varying flow and discharge temperature;
- depth-resolved ambient temperature, salinity and current;
- historical replay from providers such as Copernicus Marine;
- later live probe / plant / SCADA providers through the same forcing contract;
- near-field plume prediction plus a separately qualified simple far-field layer;
- section/plan-view thermal contours and annual animations;
- configurable permit criteria such as plume extent above ΔT thresholds, surface hotspot temperature, receptor temperature and exceedance duration.

Plume does **not** aim to become a general CFD or coastal hydrodynamic model. Where currents, bathymetric steering, recirculation or shoreline physics require a 3-D hydrodynamic solution, Plume should ingest that solution rather than recreate it.

See [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md).

## Repository state

SPEC-0 reset the active product tree before implementation. CORE-0 now provides the headless package/config/provider/workspace foundation; it deliberately does **not** implement plume physics. MODEL-1 owns the first qualified single-round-port near-field kernel.

The earlier screening prototype and its experimental calibration are preserved at branch:

`archive/prototype-v0`

They are historical research, not inherited model truth.

Immutable third-party/reference distributions live under [References/](References/). Product code must never modify them.

## Configuration and local workspace

Runs are config-driven. See [docs/CONFIG.md](docs/CONFIG.md) and [configs/example.yaml](configs/example.yaml).

Generated/downloaded material belongs in the local, gitignored workspace:

```text
workspace/
  _cache/                  # reusable provider downloads, e.g. Copernicus
  projects/
    <project-id>/
      project.yaml         # added when project persistence lands
      revisions/
      runs/
        <run-id>/
          manifest.json
          config.normalized.yaml
          inputs/
          results/
          plots/
          animations/
          logs/
```

A config can choose what is retained. Heavy fields and animations can be disabled for fast engineering runs while metrics and cached forcing remain reusable.

CORE-0 exposes a small headless preparation command:

```bash
python -m plume prepare configs/example.yaml
```

This validates/normalizes schema v1, resolves deterministic local providers, and creates a prepared run directory plus provenance manifest. It does not execute plume physics.

## Credentials

Never commit credentials.

Copy `.env.example` to an ignored `.env` or inject environment variables directly. A future throwaway Copernicus account can be used in the ChatGPT sandbox without placing its password in Git history.

## Development

Read [AGENTS.md](AGENTS.md) before repository work. GitHub Actions is manual-only and requires explicit human approval; normal deterministic verification is sandbox-first.

## DESIGN-1: local Design Studio candidate

The next source candidate adds a headless pinned environmental-snapshot evaluator and local project design revisions, with a Streamlit app shell. Install with `pip install -e '.[studio]'`, then run `streamlit run apps/design_studio.py` from the repository root. See [docs/DESIGN_STUDIO.md](docs/DESIGN_STUDIO.md). Live design calculations reuse MODEL-1 + FIELD-1; data acquisition remains an explicit Ocean action. The local mode does not fetch Copernicus data. Physical closure and field-profile qualification remain **UNVALIDATED**; annual simulations and permit verdicts are future work.
