# Current build / evidence status

This file is the single owner for current repository status.

## SPEC-0 candidate — 2026-10-07

**Authoritative main at sprint start:** `b691113b374b08a21302a23e17a196a78e325fb8`.

**Historical prototype snapshot:** branch `archive/prototype-v0` points at that exact commit.

**Candidate branch:** `spec-0-product-reset`.

**Qualified reset/source head:** `57196f68f810d02f6ee825457f69565aaed7e7cb`.

### Candidate result

- active product is defined as a thermal-discharge digital twin, not the historical screening script;
- historical prototype/calibration is absent from the active candidate but preserved unchanged in Git;
- `References/` is the immutable external evidence boundary;
- the user mockup moved from `References/` to `docs/assets/initial-mockup.png`;
- product/config/provider/workspace/permit-output contracts are defined before implementation;
- generated/downloaded data defaults to ignored `workspace/`;
- credentials are excluded from source;
- GitHub Actions remains manual-only.

### Structural evidence

Against `57196f68f810d02f6ee825457f69565aaed7e7cb`:

- top-level active tree is limited to `.env.example`, `.github`, `.gitignore`, `AGENTS.md`, `README.md`, `References/`, `configs/`, and `docs/`;
- active tree contains **no Python implementation files** and no `requirements.txt`;
- `archive/prototype-v0` remains exactly `b691113b374b08a21302a23e17a196a78e325fb8`;
- PLUMES reference files are byte-identical relative to sprint start; the only `References/` diff is the user-owned mockup rename into docs;
- example config YAML parses and passes a focused contract smoke check;
- manual workflow YAML parses and exposes only `workflow_dispatch`;
- no GitHub Actions run was started on `spec-0-product-reset`.

### Reference research

- Both checked-in PLUMES distributions contain executables and data, not Fortran source.
- The EPA Dec-2025 package contains useful additional near-/far-field traces.
- No authentic public PLUMES2.0 Fortran source was found in the 2026-10-07 EPA/SSMC/web/GitHub search.
- Public SFEI Visual Plumes/UM3 Python code (GPL-3.0) and Ebb Carbon PLUMES2.0 Python port (MIT) were identified as valuable independent references.

### Evidence policy for this sprint

SPEC-0 changes repository/product contracts, not plume physics. No GitHub Actions run is required or authorised.

### Integration state

**READY FOR INTEGRATION.** Merge authority remains human-only.

The next seams after integration are **REF-1** (reference qualification) and **CORE-0** (package/config/workspace skeleton).
