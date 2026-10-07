# Backlog

Live queue. Item numbers are identities, not priority. A ready item names the observation that retires it.

## What is next

### P0-1 — Bootstrap repository workflow
**State:** RETIRED when this document is on authoritative `main`; otherwise READY FOR INTEGRATION on `bootstrap/plume-workflow-v1`.

**Evidence:** repository owners exist; model/source head `32a4dda49b9904698e15b5102197c2a93abea6e9` passed the bootstrap Python verification before the Actions-credit policy changed; later changes are workflow/docs only. The sandbox-first workflow was mechanically verified to expose only manual `workflow_dispatch`, with no automatic push/PR/schedule trigger. PLUMES reference capture is explicitly routed to P0-2 / `PLUMES-REF-1`.

**Retires when:** this bootstrap content is integrated to `main`.

### P0-2 — Capture canonical PLUMES2.0 golden cases
**Why:** the archived reference is a Windows executable and cannot currently run in the remote Linux sandbox.

**Scope:** choose a small representative first set (baseline warm discharge, high/low momentum, crossflow, shallow/deep or stratified as supported), run the exact archived executable on Windows, preserve exact inputs and raw outputs outside `PLUMES2.0-main/`, and record executable SHA-256/version/environment.

**Retires when:** committed golden evidence can reproduce the exact reference outputs without relying on chat memory.

### P0-3 — Build PLUMES output parser + comparison harness
**Scope:** parse preserved raw PLUMES text into normalized trajectory/dilution data and compare the Python model using named metrics.

**Retires when:** the sandbox can run at least one golden case, a deliberate plausible mismatch goes red, and the report identifies exact reference/candidate identities. An optional GitHub Actions cross-check requires explicit human approval.

### P1-1 — Convert prototype checks to a normal Python test layout
Move toward `src/` + `tests/` and pytest only after the reference baseline is pinned.

**Retires when:** imports/tests are package-stable, current self-test coverage is preserved, and the sandbox verification is green.

### P1-2 — Define comparison acceptance bands from evidence
Do not invent tolerances before seeing reference behaviour and numerical repeatability.

**Retires when:** named metrics/tolerances are justified in a durable decision/model note and include independent hold-back cases.

### P2-1 — Independent validation strategy
Define the role of CORMIX, literature/experiment data, and site-specific engineering checks after PLUMES regression is working.

**Retires when:** we can distinguish calibration, reference regression, and independent physical validation without conflating them.
