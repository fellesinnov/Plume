"""Simple one-click case runner for the thermal outfall screening model.

Edit the CONFIG dictionary at the top and run this file in VS Code or a terminal:
    python quick_case_runner.py

It automatically:
- picks a pipe diameter near the chosen target velocity;
- runs the 4°C, 3°C and 2°C mixing-zone criteria;
- saves a plot for each case; and
- prints a short summary of the approximate distance to reach each criterion.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from outfall_screen import OutfallCase, plot_case, simulate

CONFIG = {
    "case_id": "case_3000_7m_2mps",
    "flow_m3h": 3000.0,
    "target_velocity_mps": 2.0,
    "sea_temp_C": 20.0,
    "delta_T_C": 7.0,
    "water_depth_m": 10.0,
    "discharge_depth_below_surface_m": 7.0,
    "current_mps": 0.0,
    "current_direction_deg": 90.0,
    "design_factor": 1.5,
    "criteria_C": [4.0, 3.0, 2.0],
    "output_dir": "example_outputs/quick_case",
}

COMMON_DN_M = [
    0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50,
    0.60, 0.65, 0.70, 0.75, 0.80, 0.90, 1.00, 1.20,
]


def calc_required_diameter_m(flow_m3h: float, target_velocity_mps: float) -> float:
    q = flow_m3h / 3600.0
    area = q / target_velocity_mps
    diameter = math.sqrt((4.0 * area) / math.pi)
    return diameter


def pick_standard_diameter_m(flow_m3h: float, target_velocity_mps: float) -> tuple[float, float]:
    required = calc_required_diameter_m(flow_m3h, target_velocity_mps)
    candidates = COMMON_DN_M
    selected = min(candidates, key=lambda d: abs((flow_m3h / 3600.0) / (math.pi * d * d / 4.0) - target_velocity_mps))
    return required, selected


def run_case_set(config: dict) -> pd.DataFrame:
    flow = float(config["flow_m3h"])
    target_v = float(config["target_velocity_mps"])
    required_d, selected_d = pick_standard_diameter_m(flow, target_v)

    water_depth = float(config["water_depth_m"])
    discharge_depth = float(config["discharge_depth_below_surface_m"])
    port_height = water_depth - discharge_depth
    if port_height <= 0:
        raise ValueError(
            f"Discharge depth {discharge_depth} m below surface is not valid for a water depth of {water_depth} m."
        )

    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for allowed_dt in config["criteria_C"]:
        case = OutfallCase(
            flow_m3h=flow,
            diameter_m=selected_d,
            sea_temp_C=float(config["sea_temp_C"]),
            delta_T_C=float(config["delta_T_C"]),
            water_depth_m=water_depth,
            port_height_m=port_height,
            current_mps=float(config["current_mps"]),
            current_direction_deg=float(config["current_direction_deg"]),
            allowed_delta_T_C=float(allowed_dt),
            design_dilution_factor=float(config["design_factor"]),
            case_id=f"{config['case_id']}_dt{allowed_dt:g}C",
        )
        result = simulate(case)
        summary = result["summary"]
        source = result["source"]

        row = {
            "case_id": case.case_id,
            "flow_m3h": flow,
            "target_velocity_mps": target_v,
            "required_diameter_m": required_d,
            "selected_diameter_m": selected_d,
            "water_depth_m": water_depth,
            "discharge_depth_below_surface_m": discharge_depth,
            "port_height_m": port_height,
            "sea_temp_C": case.sea_temp_C,
            "delta_T_C": case.delta_T_C,
            "allowed_delta_T_C": allowed_dt,
            "required_dilution": source["required_dilution"],
            "green_design_dilution": source["green_design_dilution"],
            "status": summary["status"],
            "termination": summary["termination"],
            "required_reached_horizontal_m": summary["required_reached_horizontal_m"],
            "required_reached_s_m": summary["required_reached_s_m"],
            "green_reached_horizontal_m": summary["green_reached_horizontal_m"],
            "termination_horizontal_distance_m": summary["termination_horizontal_distance_m"],
            "termination_centerline_delta_T_C": summary["termination_centerline_delta_T_C"],
            "termination_centerline_dilution": summary["termination_centerline_dilution"],
            "warnings": " | ".join(summary["warnings"]),
        }
        rows.append(row)

        plot_path = output_dir / f"{case.case_id}.png"
        plot_case(result, plot_path)

    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(output_dir / "summary.csv", index=False)
    return summary_df


def print_summary(df: pd.DataFrame) -> None:
    print("\n=== Quick case summary ===")
    print(f"Target flow: {df['flow_m3h'].iloc[0]:.0f} m3/h")
    print(f"Target velocity: {df['target_velocity_mps'].iloc[0]:.2f} m/s")
    print(f"Required diameter for target velocity: {df['required_diameter_m'].iloc[0]:.3f} m")
    print(f"Selected nearest standard pipe: {df['selected_diameter_m'].iloc[0]:.3f} m (approx {df['selected_diameter_m'].iloc[0] * 1000:.0f} mm)")
    print(f"Water depth: {df['water_depth_m'].iloc[0]:.1f} m | discharge depth below surface: {df['discharge_depth_below_surface_m'].iloc[0]:.1f} m")
    print("\nApproximate horizontal distance to each thermal criterion:")

    for _, row in df.iterrows():
        req_h = row["required_reached_horizontal_m"]
        green_h = row["green_reached_horizontal_m"]
        if req_h is None:
            req_text = "not reached before termination"
        else:
            req_text = f"{req_h:.1f} m"

        if green_h is None:
            green_text = "not reached before termination"
        else:
            green_text = f"{green_h:.1f} m"

        print(
            f"- dT <= {row['allowed_delta_T_C']:.0f} C: required dilution {row['required_dilution']:.2f}:1, "
            f"distance to meet criterion = {req_text}; green design target = {green_text}"
        )

    print("\nPlots saved in:", Path(CONFIG["output_dir"]).resolve())
    print("CSV summary saved in:", (Path(CONFIG["output_dir"]) / "summary.csv").resolve())


if __name__ == "__main__":
    summary = run_case_set(CONFIG)
    print_summary(summary)
