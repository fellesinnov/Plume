"""Run one real MODEL-1 + GSW + FIELD-1 diagnostic and save to ignored workspace.

This is a deterministic development scenario, NOT a physically validated
customer discharge. No Copernicus/API access, credentials, GUI or cache needed.

    python tools/field1_live_demo.py
    python tools/field1_live_demo.py --workspace workspace

Requires: pip install -e '.[plot]'  (GSW is a normal project dependency)
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

from plume.field import horizontal_plan, vertical_section
from plume.model import (
    AmbientColumn, AmbientLevel, GswThermodynamics,
    NearFieldOptions, NearFieldProblem, SingleRoundPort,
    SourceState, solve_near_field,
)
from plume.render import render_field_pair


def build_fixture():
    thermo = GswThermodynamics()
    latitude, longitude = 60.0, 5.0
    water_depth = 25.0
    outlet_depth = 12.0
    inlet = [
        # Positive-down depth [m], in-situ temperature [deg C], SP, east current [m/s]
        (0.0, 13.0, 34.7, 0.12),
        (10.0, 11.5, 34.9, 0.12),
        (25.0, 9.0, 35.0, 0.12),
    ]
    levels = []
    for depth, temp, sp, current in inlet:
        normalized = thermo.from_practical_salinity_in_situ(
            practical_salinity=sp, in_situ_temperature_C=temp,
            depth_m=depth, latitude_deg=latitude, longitude_deg=longitude)
        levels.append(AmbientLevel(depth, normalized, current, 0.0))
    # Document process delta T relative to the explicit local design-basis
    # in-situ ambient at outlet depth, not the surface temperature.
    ambient_at_outlet = float(np.interp(
        outlet_depth, [p[0] for p in inlet], [p[1] for p in inlet]))
    source_temp = ambient_at_outlet + 10.0
    source_state = thermo.from_practical_salinity_in_situ(
        practical_salinity=35.0, in_situ_temperature_C=source_temp,
        depth_m=outlet_depth, latitude_deg=latitude, longitude_deg=longitude)
    problem = NearFieldProblem(
        latitude_deg=latitude, longitude_deg=longitude,
        water_depth_m=water_depth,
        port=SingleRoundPort(
            diameter_m=0.35, discharge_depth_below_surface_m=outlet_depth,
            vertical_angle_deg=15.0, azimuth_deg=90.0),
        source=SourceState(flow_m3s=0.15, seawater=source_state),
        ambient=AmbientColumn.from_levels(levels),
    )
    details = {
        "scenario": "FIELD-1 deterministic inline-only demonstration",
        "location_wgs84": {"latitude_deg": latitude, "longitude_deg": longitude},
        "water_depth_m": water_depth,
        "discharge_depth_below_surface_m": outlet_depth,
        "outfall_diameter_m": 0.35,
        "outfall_azimuth_deg": 90.0,
        "outfall_vertical_angle_deg": 15.0,
        "source_flow_m3s": 0.15,
        "source_practical_salinity": 35.0,
        "source_in_situ_temperature_C": source_temp,
        "ambient": [
            {"depth_m": d, "in_situ_temperature_C": t, "practical_salinity": s,
             "east_current_mps": u}
            for d, t, s, u in inlet
        ],
        "profile_and_model_qualification": "UNVALIDATED; independent cross-plume and MODEL-1 hold-back gates open",
        "provider": "inline synthetic design-basis only (no Copernicus download)",
    }
    return thermo, problem, details


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace", type=Path, default=Path("workspace"),
        help="ignored local runtime workspace root (default: workspace)",
    )
    args = parser.parse_args()
    target = args.workspace.resolve() / "field1" / "live_gsw_demo"
    if not (target == (Path("workspace").resolve() / "field1" / "live_gsw_demo")
            or args.workspace.is_absolute()):
        # Relative overrides are user-controlled output paths; warn without
        # constraining the documented configurable workspace choice.
        print(f"FIELD-1 output workspace override: {target}", file=sys.stderr)
    target.mkdir(parents=True, exist_ok=True)

    thermo, problem, provenance = build_fixture()
    options = NearFieldOptions(max_time_s=8.0, oscillation_event_limit=20)
    result = solve_near_field(problem, thermodynamics=thermo, options=options)
    trajectory = result.sample(np.linspace(0.0, result.end_time_s, 260))
    horiz_extent = max(
        4.0, float(np.max(trajectory.x_east_m)) + 2.0)
    plan_depth = float(np.median(trajectory.depth_m))

    section = vertical_section(
        result, distances_m=np.linspace(-0.5, horiz_extent, 230),
        depths_m=np.linspace(0.0, problem.water_depth_m, 155),
        heading_deg=90.0, samples=260)
    plan = horizontal_plan(
        result, east_m=np.linspace(-0.5, horiz_extent, 230),
        north_m=np.linspace(-3.0, 3.0, 105),
        depth_m=plan_depth, samples=260)
    if not (section.values.modeled.any() and plan.values.modeled.any()):
        raise RuntimeError("no physical reconstructed near-field support on section or plan")

    fig = render_field_pair(
        section, plan, threshold_delta_T_C=2.0,
        title="Plume FIELD-1  /  MODEL-1 + TEOS-10 (synthetic inline forcing)")
    outfile = target / "model1_gsw_field1_section_plan.png"
    fig.savefig(outfile, dpi=160, facecolor=fig.get_facecolor())
    import matplotlib.pyplot as plt
    plt.close(fig)

    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            check=True, timeout=4,
        ).stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        sha = "unavailable"
    provenance.update({
        "nearfield_options": {
            "max_time_s": options.max_time_s,
            "oscillation_event_limit": options.oscillation_event_limit,
            "closure": str(options.closure),
        },
        "model_git_sha": sha,
        "termination_reason": str(result.reason),
        "end_time_s": float(result.end_time_s),
        "final_dilution_bulk": float(trajectory.dilution[-1]),
        "field_profile_id": section.values.profile_id,
        "section_peak_excess_C": float(section.values.delta_temperature_C.max()),
        "plan_peak_excess_C": float(plan.values.delta_temperature_C.max()),
        "plan_slice_depth_m": plan_depth,
        "figure": outfile.name,
        "GSW": "official GSW-Python through GswThermodynamics",
    })
    (target / "provenance.json").write_text(
        json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    print(f"FIELD-1 real model/GSW demo PNG: {outfile}")
    print(f"MODEL termination: {result.reason}; end time {result.end_time_s:.3f} s")
    print(f"Final bulk dilution: {trajectory.dilution[-1]:.3f}")
    print("QUALIFICATION: unvalidated; MODEL-CLOSURE-1/FIELD-PROFILE-1 remain open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
