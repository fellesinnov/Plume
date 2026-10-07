# AGENTS.md — Plume

Agent entry point for this repository. Keep this file short; detailed method and current evidence live under `docs/`.

## Before doing work

Read these in order before changing repository content:

1. [docs/METHOD.md](docs/METHOD.md) — development and evidence method.
2. [docs/buildlog/README.md](docs/buildlog/README.md) — current status and evidence boundary.
3. [docs/USER_INPUT.md](docs/USER_INPUT.md) and [docs/BACKLOG.md](docs/BACKLOG.md) — accepted human direction and live queue.
4. [docs/GATES.md](docs/GATES.md) — unresolved reference/manual evidence.
5. [docs/MODEL_REFERENCE.md](docs/MODEL_REFERENCE.md) — immutable PLUMES2.0 reference contract.
6. For modelling work, read [MODEL_NOTES.md](MODEL_NOTES.md), [SCREENING_PROCEDURE.md](SCREENING_PROCEDURE.md), then inspect the implementing Python and relevant tests/data.

When written claims disagree, check the implementing code. The implementation is evidence for current behaviour; accepted model/reference decisions define intended behaviour; `docs/buildlog/README.md` owns current evidence/status.

## Immutable reference boundary

**Never modify anything under `PLUMES2.0-main/` during normal product/model work.**

That directory is the archived reference distribution used to generate comparison evidence. Do not edit, reformat, regenerate, rename, delete, or "fix" files inside it. Any future upstream refresh must be its own explicitly human-authorised archive-import sprint with before/after identities and provenance.

Reference-model agreement is not physical validation and must never be described as permitting proof.

## Working agreement

- Work in explicit, decision-coherent sprints. At sprint start state scope, retirement evidence, and recommended reasoning level.
- Count judgements, not files. Plan before changing more than two independent decisions.
- Check behavioural/model claims against the function that implements them before planning from prose.
- Every backlog item must name the observation that retires it.
- Every important deterministic gate should have a real failure discriminator where practical.
- Route every finding to `BACKLOG.md`, `GATES.md`, a durable model/decision owner, or a buildlog before clearing context.
- Preserve units and conventions explicitly. Do not silently change coordinate systems, bulk/centerline definitions, density conventions, calibration meanings, or termination semantics.
- Separate calibration cases from verification/hold-back cases. Do not tune a coefficient against a case and then cite that same case as independent verification.
- Prefer the simplest current architecture; this repository is still prototype-stage and does not owe backward compatibility unless a future owner says otherwise.

## Actor model

The normal path is deliberately lighter than BOOSTED:

- **ChatGPT + GitHub**: architecture, source authoring, review, repository status, durable evidence and branch/PR work.
- **GitHub Actions / sandbox**: normal mechanical closer for Python syntax, regression tests and deterministic batch checks.
- **Local Luna/Windows**: exception path for evidence that specifically requires the archived Windows PLUMES executable, GUI interaction, or another OS-local dependency.
- **Human**: modelling/product judgement, acceptance of ambiguous engineering policy, and final merge authority.

Use one writer lease at a time. Connector-authored source is a candidate until the required automated evidence is green. Do not make the human relay routine Python failures that CI can establish directly.

## Verification and completion

For ordinary Python/model work, close the deterministic boundary with the repository CI workflow. A physics/closure/trajectory/dilution change additionally owes the relevant PLUMES reference comparison once the golden-reference harness exists.

State exactly what was tested and what remains unproven. Never upgrade:

- "CI green" to "validated",
- "matches PLUMES" to "physically correct",
- one platform/reference case to a general support or applicability claim.

At integration checkpoints recommend **merge/integrate now** or **hold**, with blockers. Never merge `main` without explicit human authorisation.
