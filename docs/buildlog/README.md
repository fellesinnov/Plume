# Current build / evidence status

This file is the single owner for current repository status.

## SPEC-0 candidate — 2026-10-07

**Authoritative main at sprint start:** `b691113b374b08a21302a23e17a196a78e325fb8`.

**Historical prototype snapshot:** branch `archive/prototype-v0` points at that exact commit.

**Candidate branch:** `spec-0-product-reset`.

### Candidate intent

- active product becomes a thermal-discharge digital twin, not the historical screening script;
- historical prototype/calibration is removed from the active candidate but preserved in Git;
- `References/` is the immutable external evidence boundary;
- user mockup moves from `References/` to documentation assets;
- product/config/provider/workspace/permit-output contracts are defined before implementation;
- generated/downloaded data defaults to ignored `workspace/`;
- credentials are excluded from source;
- GitHub Actions remains manual-only.

### Reference research

- Both checked-in PLUMES distributions contain executables and data, not Fortran source.
- The EPA Dec-2025 package contains useful additional near-/far-field traces.
- No authentic public PLUMES2.0 Fortran source was found in the 2026-10-07 EPA/SSMC/web/GitHub search.
- Public SFEI Visual Plumes/UM3 Python code (GPL-3.0) and Ebb Carbon PLUMES2.0 Python port (MIT) were identified as potentially valuable independent references.

### Evidence policy for this sprint

SPEC-0 changes repository/product contracts, not plume physics. No GitHub Actions run is required or authorised. Qualification is structural/document review plus exact remote-tree inspection.

### Integration state

**CANDIDATE — do not merge without explicit human authorisation.**

The next implementation/reference seams after integration are REF-1 and CORE-0.
