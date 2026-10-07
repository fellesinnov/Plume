# Plume development method

This method is intentionally lightweight. It preserves the useful evidence discipline from earlier projects without turning a Python engineering model into a release-process project.

## 1. Core rules

1. **Product/spec before implementation.** A modelling or data feature must fit [PRODUCT_SPEC.md](PRODUCT_SPEC.md) or be raised as a product decision.
2. **Check claims against implementation/evidence.** Several documents repeating a statement are still one claim.
3. **Chunk by decisions, not file count.** Large mechanical edits with one settled decision are safer than tiny edits that hide several modelling judgements.
4. **Every backlog item names retirement evidence.**
5. **Important deterministic gates must be capable of failing.**
6. **Route findings out of chat.** Use backlog, gates, spec/reference owners or buildlog.
7. **Automate cheap evidence; preserve scarce resources.** Sandbox first. GitHub Actions only after explicit human approval.

## 2. Evidence ladder

Use precise language:

- **Source candidate** — source/docs exist but required deterministic evidence is not complete.
- **Sandbox green** — required deterministic checks passed in the ChatGPT sandbox against the named identity.
- **Actions green** — an explicitly human-approved GitHub Actions run passed on the named commit.
- **Reference compared** — the exact candidate was compared with preserved external/reference output for named cases/metrics.
- **Externally checked** — compared with independent implementation, experiment, site data or another appropriate source.
- **Human accepted** — the maintainer accepts the modelling/product judgement.

Higher levels do not happen automatically. Reference parity is not physical validation.

## 3. Default actor split

ChatGPT + GitHub owns coherent remote authoring/review and repository evidence. The ChatGPT sandbox is the default mechanical closer.

GitHub Actions is **manual opt-in**. Never dispatch or automatically enable an Actions run without explicit human approval for that run. If sandbox evidence establishes the claim, do not spend Actions credits merely to duplicate it.

Use local Windows/Luna only when the remaining evidence specifically requires a Windows-only reference executable or another local dependency.

The human owns product/modelling judgement, permission to spend Actions credits and merge authority.

## 4. Config/workspace rule

Product behaviour is config-driven.

- Schema changes are product/API decisions and require explicit versioning.
- UI-specific state must not become the only representation of a run.
- Runtime downloads, caches, generated fields, plots, animations and reports belong in the configured gitignored workspace.
- Every run eventually owes a manifest linking normalized config, model identity and provider/input provenance.
- Credentials are environment state, never config/source state.

## 5. Model-change rule

A change to equations, closure coefficients, source terms, density treatment, coordinates, stopping conditions, dilution definitions, field reconstruction, calibration or permit metrics should normally include:

- a focused deterministic regression/invariant;
- a trend/conservation check where meaningful;
- mechanism and expected direction;
- relevant reference comparison;
- independent hold-back verification if any parameter was calibrated.

Do not tune against all available cases and then call the same cases verification.

## 6. External source/reference code

`References/` is immutable evidence.

Public implementations discovered elsewhere can be extremely useful for understanding behaviour and designing tests, but copying/adapting source is a separate license/provenance decision.

In particular:

- permissively licensed code may be considered for adaptation with attribution after an explicit decision;
- GPL code should be treated as an external reference unless the human explicitly chooses a GPL-compatible product strategy;
- a third-party reimplementation is not automatically equivalent to the selected PLUMES2.0 executable.

## 7. Integration

Before recommending integration:

- exact branch/head is verified remotely;
- required sandbox/structural evidence is green;
- no unapproved Actions run occurred;
- buildlog/backlog/gates reflect the candidate;
- reference/model debt is stated honestly;
- unresolved human judgement is not disguised as test debt.

The human explicitly authorises merge.
