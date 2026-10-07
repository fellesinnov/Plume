# Current build / evidence status

This file is the single owner for current repository status.

## SPEC-0 candidate — 2026-10-07

**Authoritative main at sprint start:** `b691113b374b08a21302a23e17a196a78e325fb8`.

**Historical prototype snapshot:** branch `archive/prototype-v0` points at that exact commit.

**Candidate branch:** `spec-0-product-reset`.

**Qualified reset/source commit:** `57196f68f810d02f6ee825457f69565aaed7e7cb`.

**Current candidate head:** `a13c7952e9e6f08c02c6d2b1ce7a4ca527639fcb`.

### Candidate result

- active product is defined as a thermal-discharge digital twin, not the historical screening script;
- historical prototype/calibration is absent from the active candidate but preserved unchanged in Git;
- `References/` is the immutable external evidence boundary;
- the user mockup moved from `References/` to `docs/assets/initial-mockup.png`;
- product/config/provider/workspace/permit-output contracts are defined before implementation;
- an explicit **Design Mode** now precedes annual simulation: evaluate one representative/adverse snapshot, compare outlet geometry/operation, then lock the selected normal config;
- outlet architecture is type-tagged/extensible: single round port first, multiport and other outlet geometries later through adapters;
- generated/downloaded data defaults to ignored `workspace/`;
- credentials are excluded from source;
- GitHub Actions remains manual-only;
- reference policy is accuracy-first triangulation, not PLUMES2.0 parity as physical truth;
- SFEI GPL-3.0 Visual Plumes may be used as an external oracle; the MIT Ebb PLUMES2.0 port is a serious reuse candidate after REF-1 review.

### Structural evidence

Against the qualified reset/source commit:

- top-level active tree is limited to `.env.example`, `.github`, `.gitignore`, `AGENTS.md`, `README.md`, `References/`, `configs/`, and `docs/`;
- active tree contains **no Python implementation files** and no `requirements.txt`;
- `archive/prototype-v0` remains exactly `b691113b374b08a21302a23e17a196a78e325fb8`;
- PLUMES reference files are byte-identical relative to sprint start; the only `References/` diff is the user-owned mockup rename into docs;
- example config YAML parses and passes a focused contract smoke check;
- manual workflow YAML parses and exposes only `workflow_dispatch`;
- no GitHub Actions run has been started on `spec-0-product-reset`.

Subsequent commits through the current head are documentation/specification refinements only.

### Reference research

- Both checked-in PLUMES distributions contain executables and data, not Fortran source.
- The EPA Dec-2025 package contains useful additional near-/far-field traces.
- No authentic public PLUMES2.0 Fortran source was found in the 2026-10-07 EPA/SSMC/web/GitHub search.
- Public SFEI Visual Plumes/UM3 Python code (GPL-3.0) and Ebb Carbon PLUMES2.0 Python port (MIT) were identified as valuable independent references.

### Evidence policy for this sprint

SPEC-0 changes repository/product contracts, not plume physics. No GitHub Actions run is required or authorised.

### Design Studio refinement

- UI/product contract added at `docs/UI_SPEC.md` on qualified spec head `365ef1de50d4cad193f62abdf80f27bab8ddd0bd`.
- Preferred first shell is Streamlit, but physics/providers/config/cache/criteria stay headless.
- Workflow is `Project → Ocean → Design → Simulate → Results`.
- Ocean data is fetched/cached explicitly; selecting/designing against a pinned timestamp never refetches on geometry changes.
- Named customer/site projects and revisions remain under gitignored `workspace/projects/` by default.
- Provider, physics and render caches invalidate independently.
- Annual runs always retain compact metrics/provenance but need not retain dense spatial fields for every timestep.
- No GitHub Actions run was required or authorised for this docs/spec refinement.

### Integration state

**READY FOR INTEGRATION.** Merge authority remains human-only under current repository governance.

The next seam after integration is **REF-1 reference bakeoff**, followed by **CORE-0**, **MODEL-1**, **FIELD-1**, then **DESIGN-1** before historical TIME-1.
