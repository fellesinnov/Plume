# Proposed internal screening procedure

## Objective

Use this tool only to answer:

> Can a simple single submerged pipe satisfy a deliberately conservative thermal criterion through
> outlet-generated near-field mixing, with enough margin that far-field oceanography is not needed to
> justify the concept?

## Stage A - Source definition

Required:

1. maximum discharge flow;
2. port internal diameter;
3. ambient sea temperature;
4. process temperature rise;
5. ambient salinity;
6. effluent salinity (default same as ambient for once-through cooling water);
7. local minimum water depth;
8. port-center height above seabed;
9. outlet vertical angle.

Calculated:

- exit velocity;
- absolute discharge temperature;
- source/ambient density;
- reduced gravity;
- heat load;
- source Froude number;
- jet/plume transition scale.

## Stage B - Compliance target

For a screening temperature rise `dT_allow`:

`S_required = dT_process / dT_allow`

Proposed internal starting values:

- `dT_allow = 1 C`
- design dilution factor = `1.5`

For a +10 C process rise:

- required centerline dilution = 10:1;
- GREEN design target = 15:1.

These are internal screening choices and must not be presented as universal regulatory limits.

## Stage C - Base "independence from the ocean" case

Run:

- no atmospheric cooling;
- no far-field diffusion;
- uniform ambient density;
- zero ambient current;
- minimum local water depth;
- single round port.

This is not claimed to be the universal permit worst case. Its role is to test whether the outlet can solve the
thermal problem largely by itself.

## Stage D - Environmental envelope

For concepts that approach GREEN, run the standard T/S/current envelope.

Add explicit stratified cases when relevant.

A concept should not be upgraded to GREEN merely because current improves dilution. The no-current result remains
a useful robustness indicator.

## Stage E - GREEN gate

Proposed GREEN requires:

1. centerline dilution reaches `1.5 x S_required`;
2. this occurs before surface, bottom, neutral-buoyancy, shore/receptor-clearance termination;
3. target is reached before 60% of the available modeled near-field path;
4. no source-geometry or strong-current applicability warning;
5. calibration/verification envelope includes the case regime.

AMBER means CORMIX/PLUMES check, geometry optimization, or both.

RED means the simple pipe does not independently solve the screen; investigate smaller/faster port, greater
submergence, revised angle, reduced process delta-T, or diffuser.

## Stage F - Automatic advanced-analysis triggers

Regardless of the simple result, trigger CORMIX/PLUMES and potentially far-field hydrodynamics for:

- tidal reversal or recirculation;
- enclosed/semi-enclosed receiving water;
- near shoreline/breakwater interaction;
- important bathymetric steering;
- pycnocline/trapping;
- nearby intake;
- sensitive receptor;
- multiport diffuser/plume merging;
- dense/brine discharge;
- reliance on far-field dilution;
- permit-defined mixing-zone geometry that must be explicitly demonstrated.

## Stage G - Model qualification

Before this screen is adopted as an internal "stop analysis" gate:

1. calibrate closure coefficients against selected CORMIX/CorJet cases;
2. hold back independent CORMIX cases;
3. cross-check selected cases in PLUMES2.0;
4. compare against published round buoyant-jet laboratory benchmarks;
5. freeze coefficients and software version;
6. document error statistics and applicability limits.
