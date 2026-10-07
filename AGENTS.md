# AGENTS.md — Plume

Agent entry point for this repository. Detailed product, method and evidence owners live under `docs/`.

## Before doing work

Read these in order before changing repository content:

1. [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) — what Plume is and is not.
2. [docs/METHOD.md](docs/METHOD.md) — development and evidence method.
3. [docs/buildlog/README.md](docs/buildlog/README.md) — current status and evidence boundary.
4. [docs/USER_INPUT.md](docs/USER_INPUT.md) and [docs/BACKLOG.md](docs/BACKLOG.md) — accepted human direction and live queue.
5. [docs/GATES.md](docs/GATES.md) — unresolved evidence/judgement gates.
6. [docs/CONFIG.md](docs/CONFIG.md) — config, provider and local-workspace contracts.
7. [docs/MODEL_REFERENCE.md](docs/MODEL_REFERENCE.md) — immutable external model/reference contract.

For implementation work, inspect the implementing code and relevant tests/data after reading the owners above. When prose disagrees with implementation, check the implementation before making behavioural claims; accepted product/model decisions define intended behaviour and `docs/buildlog/README.md` owns current evidence/status.

## Immutable reference boundary

**Never modify files under `References/` during normal product/model work.**

`References/` contains verbatim third-party/reference distributions used as evidence. Do not edit, reformat, regenerate, rename, delete, or "fix" their contents. A new upstream snapshot is a separate explicitly human-authorised reference-import sprint with provenance and before/after identities.

Reference agreement is not physical validation and must never be described as permitting proof.

## Product boundary

Plume is a permit-oriented **thermal-discharge digital twin engine**:

- fixed outfall/site geometry;
- time-varying flow, discharge temperature, ambient temperature/salinity profiles and current;
- near-field thermal plume physics first;
- prescribed-current/simple far-field only as a separate model layer;
- historical replay (for example Copernicus) and later live probe/SCADA providers through the same data contracts;
- permit-relevant thermal metrics, plots and animations.

Thermal effects are the product scope. Chemistry/pollutant modules in reference models are reference material, not Plume product requirements.

The active implementation must remain UI-independent so a future light integration in HeatHandler or another application can call the same core package.

## Config, workspace and secrets

- Product behaviour is driven by versioned config files, not UI state.
- Config encoding may be YAML or JSON; the normalized schema is the contract.
- Runtime data, provider caches, generated plots, animations and reports belong in a configurable **gitignored workspace** (default `workspace/`), not in source control.
- Every run must preserve enough manifest/provenance information to reproduce which config, model version and input data produced it.
- Never commit credentials. Local credentials use environment variables / ignored `.env` files. GitHub Secrets are only for explicitly human-approved Actions runs.

## Working agreement

- Work in explicit, decision-coherent sprints. At sprint start state scope, retirement evidence, and recommended reasoning level.
- Count judgements, not files. Plan before changing more than two independent decisions.
- Every backlog item names the observation that retires it.
- Important deterministic gates should have a plausible failure discriminator where practical.
- Route findings to `BACKLOG.md`, `GATES.md`, a durable spec/reference owner, or buildlog before clearing context.
- Preserve units, coordinates, dilution definitions and reference conventions explicitly.
- Separate calibration cases from verification/hold-back cases.
- Prefer the simplest current architecture. Prototype history does not create backward-compatibility obligations.
- **Sandbox first, Actions by permission.** Prove everything practical in the ChatGPT sandbox. Never dispatch or enable GitHub Actions without explicit human approval for that run.

## Actor model

- **ChatGPT + GitHub**: architecture, source authoring/review, repository status, durable evidence, branches and PRs.
- **ChatGPT sandbox**: default deterministic closer whenever the needed environment can be reproduced there.
- **GitHub Actions**: manual opt-in cross-check only after explicit human approval.
- **Local Windows/Luna**: exception path for evidence that specifically requires a Windows-only reference executable or other local dependency.
- **Human**: product/modelling judgement, permission to spend Actions credits, and final merge authority.

Use one writer lease at a time. Do not reset/force/auto-stash around conflicting writer state.

## Verification and completion

State exactly what was tested and what remains unproven. Never upgrade:

- "sandbox green" or "CI green" to "validated";
- "matches PLUMES/Visual Plumes" to "physically correct";
- one reference case to a general applicability or permitting claim.

At integration checkpoints recommend **integrate now** or **hold**, with blockers. Never merge `main` without explicit human authorisation.
