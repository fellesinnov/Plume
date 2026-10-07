# External model/reference contract

## 1. Immutable boundary

Everything under `References/` is reference evidence and read-only during normal development.

Current PLUMES distributions:

### `References/PLUMES2.0-main/`
Current UW/SSMC-style distribution checked into Plume.

Observed:
- `plumes2.0v1.exe` (Windows AMD64);
- manuals;
- example project/input/output;
- license/disclaimer/resources;
- no Fortran source files.

### `References/plumes2.0_12_22_2025/PLUMES2.0_12_22_2025/`
EPA December-2025 package.

Observed:
- a different `plumes2.0.exe` binary;
- multiple project/input files;
- raw near-/far-field material including `tempnf.utl`, `tempfl.utl`, `summarynf.utl`, `IndpFarfieldCalc.dat`;
- `fort.100`, which is formatted model/project data, **not Fortran source**;
- no `.f`, `.for`, `.f90`, `.f95`, `.f03` or `.f08` source files.

Do not modify either distribution to make comparison easier. Derived parsers, golden cases and normalized data live outside `References/`.

## 2. Public-source search — 2026-10-07

SPEC-0/REF-1 discovery searched:

- US EPA PLUMES2.0 page and manual;
- public SSMC/UW PLUMES2.0 repository/history;
- other visible SSMC/UW repositories;
- broader web/GitHub queries for PLUMES2.0, UM3, FVCOM-plume and Fortran source.

**Outcome:** no authentic public PLUMES2.0 Fortran source distribution was found.

The EPA/SSMC manual states that Lakshitha Premathilake developed/tested the Fortran UM3 implementation and that Walter Frick supplied the older UM3 code written in Pascal which formed the foundation. The manual also identifies FVCOM-plume as a Fortran ancestor containing a UM3-based initial-dilution module.

Useful public links:

- EPA PLUMES2.0: https://www.epa.gov/hydrowq/PLUMES2
- SSMC PLUMES2.0: https://github.com/ssmc-uw/PLUMES2.0
- PNNL FVCOM-plume background: https://www.pnnl.gov/ssm-marine-pollution-outfall-plume-model

The source-search gate is therefore closed as "not publicly found", not as proof that source does not exist privately. Reopen if EPA/PNNL/SSMC publishes or supplies authentic source.

## 3. Additional public implementations discovered

### SFEI Visual-Plumes-Models
https://github.com/sfei/Visual-Plumes-Models

Public Python core for Visual Plumes/UM3, including ambient profiles, UM3 near field, Brooks far field, tidal buildup and timeseries handling.

License observed: **GPL-3.0**.

Project policy: this implementation may be used aggressively as an external executable/behavioural/reference oracle. Direct copying/linking/adaptation into Plume remains a deliberate deployment/license decision so that future customer-installed software remains flexible. Its GPL license is not a reason to avoid running it for model comparison.

### Ebb Carbon Plumes_Public
https://github.com/ebbcarbon/Plumes_Public

Public **MIT-licensed** Python reimplementation of PLUMES2.0 with extensive executable trace/reference cases and decoded file/physics notes. Its README states that upstream ships without source and that the port was reconstructed from manuals, literature and executable traces.

Project policy: review it as a serious candidate implementation source rather than assuming we should independently rebuild UM3. Reuse/adaptation is acceptable with explicit provenance/attribution if its physics, tests and interfaces are suitable.

## 4. Reference strategy — triangulation, not hierarchy

PLUMES2.0 is useful evidence, not sacred truth.

REF-1 should deliberately compare:

- both checked-in PLUMES2.0 executable releases;
- SFEI Visual Plumes/UM3;
- Ebb Carbon's MIT PLUMES2.0 port;
- published governing theory / laboratory or field evidence;
- later, site/probe observations.

Reference disagreements are first-class findings. Do not average them away or force Plume to match a known implementation defect merely for parity.

Roles may differ by mechanism:

- one source may be strongest for near-field trajectory/dilution;
- another for multiport/merging;
- another for similarity profiles/isopleths;
- another for far-field Brooks behaviour;
- independent measurements/literature ultimately matter more for physical accuracy.

The outcome of REF-1 is therefore an evidence-backed implementation plan and benchmark matrix, not the coronation of one "primary truth" executable.

## 5. Calibration and verification

Use separate sets:

- **mechanism/calibration cases** to identify coefficients or choose between formulations;
- **hold-back cases** never used for fitting;
- where site measurements later calibrate a digital twin, reserve independent times/locations/conditions for verification.

A model can match reference software and still be physically wrong. A model can also intentionally differ from a reference when the reference has a documented defect and independent evidence supports the difference.

## 6. Golden/reference evidence layout

Derived evidence lives outside `References/`. REF-1A establishes the first concrete layout:

```text
tools/reference_harness/          # stdlib-only parsers/identity helpers; not product runtime
tests/reference/
  reference-lock.json             # pinned distribution/repository identities
  cases/                          # canonical case manifests
  expected/                       # small derived golden summaries
tests/reference_harness/          # parser/manifest/full-reference regressions
```

Large normalized tables should only be committed when they are genuinely useful golden material;
otherwise regenerate them from the immutable raw evidence plus the pinned manifest.

A case manifest should record:

- case ID/purpose/mechanism;
- source commit;
- reference implementation/version/path;
- executable/source digest where practical;
- runner/environment identity;
- exact inputs;
- exact raw outputs;
- any GUI choices not represented in files;
- calibration vs hold-back role.

Raw output is evidence; normalized output is derived test material.

## 7. REF-1 pinned identities and normalization

REF-1 uses exact source identities rather than floating branches:

- Ebb Carbon `ebbcarbon/Plumes_Public` at
  `9791c80ff94f706603df0ae473667ccdffd359db`;
- SFEI `sfei/Visual-Plumes-Models` at
  `99283a481a84902ab248fcf3b6041b484daa1c1e`;
- checked-in PLUMES distribution tree/executable Git identities recorded in
  `tests/reference/reference-lock.json`.

The PLUMES result normalizer names the executable's signed vertical result as `z_m`: free
surface zero, positive upward. It also derives `depth_below_surface_m = -z_m`. Flux-average
dilution and centreline dilution remain distinct quantities.

The checked-in executables are pinned by exact Git blob identity and byte size. That is the
authoritative in-repository byte identity. `tools/reference_harness/hash_reference.py` can add a
SHA-256 when an executable is exported or inspected in a binary-capable checkout, but a second
digest is not required to identify an object already pinned inside Git.

The shipped-example comparison is itself a warning about reference hygiene: both distributions
produce 55 identical near-field rows through the surface event, while the far fields differ under
different diffusivity settings. The project-file layout decoded independently by the Ebb port
places the two differing flags in the far-field eddy-diffusivity selector. Therefore the pair is a
controlled near-field cross-build check even though it is **not** a controlled far-field check.

REF-1 assigns executable roles by evidence coverage rather than release age:

- **SSMC-v1** is the primary near-field software-regression oracle because the Ebb decode and rich
  executable-trace corpus are anchored to it;
- **EPA Dec-2025** is the newer-build sentinel/secondary oracle and agrees exactly on the shipped
  near-field case;
- neither executable is a physical-truth reference.

## 8. REF-1 near-field reuse decision

The detailed mechanism matrix lives in
[`reference/REF1_NEARFIELD_BAKEOFF.md`](reference/REF1_NEARFIELD_BAKEOFF.md).

REF-1 selects:

- **Ebb MIT code as the adaptation source** for the single-port Lagrangian control-volume
  architecture, source contraction, element stretching, continuous integration and explicit
  events;
- **SFEI GPL code as an oracle/source witness only**;
- decoded UM3 current entrainment as the software-reference closure, while keeping the
  published/projected-area formulation available only for physical qualification;
- **TEOS-10** as Plume's production thermodynamic target rather than inheriting Knudsen or EOS-80;
- product coordinates as local ENU; legacy reference axes are adapter concerns.

The final physical current-entrainment closure is deliberately routed to `MODEL-CLOSURE-1`.
Fan (1967) is the formulation/calibration family; Lee & Cheung (1991) heated,
buoyancy-dominated jets are reserved as hold-back. See
[`reference/REF1_LITERATURE.md`](reference/REF1_LITERATURE.md).

## 9. Interpretation

Reference agreement can show that Plume tracks a named implementation for named cases. It does **not** by itself establish physical truth, regulatory acceptance or applicability outside the compared mechanisms/envelope.

## 10. MODEL-1 candidate implementation — 2026-10-07

The `model-1-single-port-kernel` candidate implements the REF-1 near-field reuse decision without
changing the reference hierarchy:

- product code adapts only the pinned MIT Ebb Carbon architecture/relations, with the copyright and
  MIT terms preserved in root `THIRD_PARTY_NOTICES.md`;
- SFEI Visual Plumes remains GPL oracle/reference material only; no SFEI implementation code is
  copied into the product package;
- the product state transports mass, 3-D momentum, Absolute Salinity, Conservative Temperature and
  ENU position, with GSW/TEOS-10 as the intended production thermodynamic backend;
- decoded `UM3_REFERENCE` and the published projected-area candidate are both implemented behind
  one internal entrainment interface while `MODEL-CLOSURE-1` remains open;
- selected Ebb case18/test23 and case19/test28 early-jet dilution checks are software-regression
  evidence only: 0.242 % / 0.268 % MARE respectively on the committed selected checkpoints;
- clean numerical Fan calibration/formulation observations and untouched Lee-Cheung hold-back
  observations are still owed, so the candidate does not freeze the physical closure or tolerance;
- real GSW-Python execution is separately owed by `MODEL-TEOS-1`; injected-test-double success is
  not promoted to production runtime evidence.

See `docs/buildlog/2026-10-07-model-1.md` for the exact candidate evidence and HOLD decision.

