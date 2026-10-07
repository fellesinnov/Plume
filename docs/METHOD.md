# Plume development method

This method is intentionally lightweight. It preserves useful evidence discipline without turning a Python engineering model into a release-process project.

## 1. Core rules

1. **Product/spec before implementation.** A modelling or data feature must fit [PRODUCT_SPEC.md](PRODUCT_SPEC.md) or be raised as a product decision.
2. **Check claims against implementation/evidence.** Several documents repeating a statement are still one claim.
3. **Chunk by decisions, not file count.**
4. **Every backlog item names retirement evidence.**
5. **Important deterministic gates must be capable of failing.**
6. **Route findings out of chat.**
7. **Automate cheap evidence; preserve scarce resources.** Sandbox first. GitHub Actions only after explicit human approval.
8. **Do not reinvent validated machinery without a reason.** Prefer reuse, adapters and independent cross-checks when licensing/provenance and product architecture permit it.

## 2. Evidence ladder

Use precise language:

- **Source candidate** — source/docs exist but required deterministic evidence is incomplete.
- **Sandbox green** — required deterministic checks passed in the ChatGPT sandbox against the named identity.
- **Actions green** — an explicitly human-approved GitHub Actions run passed on the named commit.
- **Reference compared** — exact candidate compared with preserved external/reference output for named cases/metrics.
- **Externally checked** — compared with independent implementation, experiment, site data or another appropriate source.
- **Human accepted** — maintainer accepts the modelling/product judgement.

Higher levels do not happen automatically. Reference parity is not physical validation.

## 3. Default actor split

ChatGPT + GitHub owns routine remote authoring/review and repository evidence. The ChatGPT sandbox is the default mechanical closer.

GitHub Actions is **manual opt-in**. Never dispatch or automatically enable an Actions run without explicit human approval for that run. If sandbox evidence establishes the claim, do not spend Actions credits to duplicate it.

Use local Windows/Luna only when remaining evidence specifically requires Windows/local state.

The human owns product/modelling judgement, permission to spend Actions credits and merge authority unless separately revised.

## 4. Config/workspace rule

Product behaviour is config-driven.

- Schema changes are product/API decisions and require explicit versioning.
- UI-specific state must not become the only representation of a run.
- Runtime downloads, caches, generated fields, plots, animations and reports belong in the configured gitignored workspace.
- Design candidates also live in the workspace; the selected candidate is exported as a normal locked config.
- Every run/design evaluation eventually owes a manifest linking normalized config, model identity and provider/input provenance.
- Credentials are environment state, never config/source state.

## 5. Model-change rule

A change to equations, closure coefficients, source terms, density treatment, coordinates, stopping conditions, dilution definitions, field reconstruction, calibration or permit metrics should normally include:

- a focused deterministic regression/invariant;
- a trend/conservation check where meaningful;
- mechanism and expected direction;
- relevant reference comparisons;
- independent hold-back verification if any parameter was calibrated.

Do not tune against all available cases and then call the same cases verification.

## 6. Reference ensemble and external code

`References/` is immutable evidence.

No external program is the sole physical truth. Use independent implementations/literature/measurements to expose disagreements.

Public code policy:

- permissively licensed code may be adapted/reused with explicit provenance and attribution when that is the best engineering path;
- GPL-3.0 programs may be run, inspected and used as external behavioural/reference oracles;
- direct copying/linking/adaptation of GPL code into Plume requires an explicit license/deployment decision because distributing that combined/derived software can create GPL obligations;
- ordinary hosted/internal use is not treated as a reason to avoid a GPL reference;
- third-party reimplementations remain independent evidence even when we decide to reuse some permissive implementation material.

## 7. Integration

Before recommending integration:

- exact branch/head is verified remotely;
- required sandbox/structural evidence is green;
- no unapproved Actions run occurred;
- buildlog/backlog/gates reflect the candidate;
- reference/model debt is stated honestly;
- unresolved human judgement is not disguised as test debt.

The human explicitly authorises merge unless repository governance is deliberately changed.
