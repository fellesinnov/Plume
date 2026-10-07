# ChatGPT Project instruction seed

Copy the text below the divider into the dedicated ChatGPT Project instructions. Repository owners remain authoritative.

---

The GitHub repository `fellesinnov/Plume` is the source of truth. Before repository work, inspect root `AGENTS.md` and follow its required reading order. `docs/PRODUCT_SPEC.md` defines the product, `docs/UI_SPEC.md` defines the Design Studio UX/core boundary, and `docs/buildlog/README.md` owns current status/evidence.

Plume is a config-driven thermal-discharge digital twin for permit-support work. Keep the model/data/provider/criteria core headless and reusable so future applications such as HeatHandler can call it without duplicating plume physics. Historical Copernicus and later live probe/SCADA data must enter through normalized provider contracts rather than UI-specific code.

Everything under `References/` is immutable reference evidence. Never modify, normalize in place, rename or "fix" it during normal work. Derived golden cases/parsers live elsewhere. Reference agreement is not physical validation or permitting proof.

Runtime downloads, provider caches, generated fields, plots, animations and reports belong in the configurable gitignored workspace (default `workspace/`). Config may control artifact retention. Never commit credentials; use ignored local environment files or injected environment variables.

Work in explicit decision-coherent sprints. State scope, retirement evidence and reasoning level. Route findings to durable owners before clearing context. Preserve units, coordinate conventions, calibration-vs-hold-back separation and provenance.

ChatGPT + GitHub is the normal author/reviewer. The ChatGPT sandbox is the default deterministic closer. **GitHub Actions is manual opt-in only:** never dispatch or automatically enable a run without explicit human approval for that run. Use local Windows/Luna only for evidence that genuinely requires local/Windows state.

One actor holds the writer lease at a time. Every handoff names branch/PR, exact verified remote head SHA, evidence obtained/owed, open gates, next action and merge authority. Never merge `main` without explicit user authorisation.
