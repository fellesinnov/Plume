# Plume development method

This is the small subset of the BOOSTED workflow that is useful for a Python engineering model.

## 1. Core rules

1. **Check the claim against the implementation.** Several documents repeating a statement are still one claim.
2. **Chunk by decisions, not file count.** Large mechanical edits with one settled decision are safer than tiny edits that hide several modelling judgements.
3. **Every backlog item names retirement evidence.** If we cannot say what observation closes it, it is not ready.
4. **A gate must be capable of failing.** Important regression checks need a plausible red case or must be labelled unproven.
5. **Keep findings out of chat-only state.** Before context is cleared, route them to backlog, gates, a model owner, or buildlog.
6. **Automate cheap evidence; preserve scarce resources.** Python syntax/tests/batches run in the ChatGPT sandbox by default. Human time belongs on modelling assumptions, interpretation and engineering usefulness. GitHub Actions credits are also scarce and are spent only after explicit human approval.

## 2. Evidence ladder

Use precise language:

- **Source candidate** — code/docs exist, but required deterministic verification is not yet green.
- **Sandbox green** — repository Python syntax/self-tests/batch smoke passed in the ChatGPT sandbox against the named source identity.
- **Actions green** — an explicitly human-approved GitHub Actions run passed on the named commit.
- **Reference compared** — the exact candidate was compared with preserved PLUMES2.0 golden output for named cases and metrics.
- **Externally checked** — compared with independent CORMIX, published experiment/data, or another appropriate source.
- **Human accepted** — the maintainer accepts the modelling/product judgement.

Higher levels do not happen automatically. In particular, PLUMES agreement is not physical validation.

## 3. Default actor split

For settled Python work, ChatGPT should author the coherent candidate remotely and close deterministic verification in the ChatGPT sandbox whenever the necessary environment can be reproduced there. A separate Codex/Luna closer is normally unnecessary.

**GitHub Actions is manual opt-in, not the default closer.** Never dispatch or automatically enable an Actions run without explicit human approval for that run. If sandbox evidence already establishes the needed claim, do not spend Actions credits to duplicate it. Use Actions when the human wants a repository-hosted cross-check or when the hosted environment itself is material to the claim.

Use local **Luna High** only when the remaining evidence specifically requires Windows/local state, especially the archived `PLUMES2.0-main/plumes2.0v1.exe`. Escalate only if that local run exposes genuinely ambiguous modelling or implementation choices.

The human owns modelling/product judgement, permission to spend GitHub Actions credits, and merge authority.

## 4. Model-change rule

A change to equations, closure coefficients, source terms, density treatment, coordinate conventions, stopping conditions, dilution definitions, calibration, or status logic should normally include:

- a focused deterministic regression or invariant;
- a trend/conservation check where meaningful;
- an explanation of the mechanism and expected direction;
- PLUMES reference comparison for affected cases once the golden harness exists;
- hold-back verification if any parameter was calibrated.

Do not tune against all available cases. Preserve independent cases that can reveal a missing mechanism rather than rewarding curve fitting.

## 5. Reference strategy

`PLUMES2.0-main/` is read-only upstream evidence. The product code never rewrites it.

Because the checked-in archive currently contains a Windows executable rather than FORTRAN source, the first reference seam is a bounded Windows capture: run named canonical cases with the archived executable and commit normalized input/output evidence outside the archive. After that, ordinary comparison tests can run without reopening the GUI.

If a trustworthy upstream FORTRAN source distribution is later added, treat that as a separate provenance/import decision. The sandbox can compile FORTRAN, but source availability and reference identity must remain explicit.

## 6. Integration

Before recommending integration:

- exact branch/head is verified remotely;
- required sandbox evidence is green;
- any GitHub Actions run was explicitly human-approved;
- model/reference debt is stated honestly;
- buildlog/backlog/gates reflect the candidate;
- unresolved human judgement is not disguised as test debt.

The human explicitly authorises merge.
