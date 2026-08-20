#!/usr/bin/env python3
"""
compare_cormix.py

Overlay the screening model against CORMIX/CorJet profile exports and optionally
fit a small number of closure parameters.

Expected CORMIX profile file:
    cormix_profiles/<case_id>.csv

Required columns:
    x_m, z_m, dilution_centerline
Optional:
    y_m

The corresponding case inputs are read from test_cases.csv (or another case CSV).

Examples
--------
python compare_cormix.py compare --cases test_cases.csv --case-id T01_baseline \
    --cormix cormix_profiles/T01_baseline.csv --plot example_outputs/T01_overlay.png

python compare_cormix.py calibrate --cases test_cases.csv \
    --profiles-dir cormix_profiles --out example_outputs/calibration_result.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from dataclasses import replace
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from outfall_screen import (
    CalibrationParams, case_from_row, simulate, plot_case
)


def load_case(cases_csv: str, case_id: str):
    df = pd.read_csv(cases_csv)
    hit = df[df["case_id"] == case_id]
    if hit.empty:
        raise ValueError(f"Case {case_id!r} not found in {cases_csv}")
    return case_from_row(hit.iloc[0])


def load_profile(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"x_m", "z_m", "dilution_centerline"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    if "y_m" not in df.columns:
        df["y_m"] = 0.0
    df["horizontal_distance_m"] = np.hypot(df["x_m"], df["y_m"])
    return df.sort_values("horizontal_distance_m").reset_index(drop=True)


def comparison_metrics(result, cormix: pd.DataFrame) -> Dict[str, float]:
    m = result["profile"].copy()
    xm = m["horizontal_distance_m"].to_numpy()
    zm = m["z_m"].to_numpy()
    dm = m["dilution_centerline"].to_numpy()

    xc = cormix["horizontal_distance_m"].to_numpy()
    valid = (xc >= xm.min()) & (xc <= xm.max())
    if valid.sum() < 3:
        raise ValueError("Too little overlapping horizontal-distance range for comparison.")

    xc = xc[valid]
    zc = cormix.loc[valid, "z_m"].to_numpy()
    dc = cormix.loc[valid, "dilution_centerline"].to_numpy()
    zi = np.interp(xc, xm, zm)
    di = np.interp(xc, xm, dm)

    # Use log dilution error so low- and high-dilution points both matter.
    log_err = np.log(np.maximum(di, 1e-9)) - np.log(np.maximum(dc, 1e-9))
    z_scale = max(result["case"]["water_depth_m"], 1.0)
    z_err = (zi - zc) / z_scale

    return {
        "n_overlap": int(valid.sum()),
        "dilution_log_rmse": float(np.sqrt(np.mean(log_err**2))),
        "dilution_mape_pct": float(np.mean(np.abs(di - dc) / np.maximum(dc, 1e-9)) * 100),
        "trajectory_z_rmse_m": float(np.sqrt(np.mean((zi-zc)**2))),
        "trajectory_z_rmse_over_depth": float(np.sqrt(np.mean(z_err**2))),
        "model_end_dilution": float(m["dilution_centerline"].iloc[-1]),
        "cormix_last_dilution_in_overlap": float(dc[-1]),
    }


def residual_vector(case, cormix, cal: CalibrationParams,
                    dilution_weight=1.0, trajectory_weight=0.5) -> np.ndarray:
    res = simulate(case, cal=cal)
    m = res["profile"]
    xm = m["horizontal_distance_m"].to_numpy()
    xc = cormix["horizontal_distance_m"].to_numpy()
    valid = (xc >= xm.min()) & (xc <= xm.max())
    if valid.sum() < 3:
        return np.array([10.0, 10.0, 10.0])

    xc = xc[valid]
    zc = cormix.loc[valid, "z_m"].to_numpy()
    dc = cormix.loc[valid, "dilution_centerline"].to_numpy()
    zi = np.interp(xc, xm, m["z_m"].to_numpy())
    di = np.interp(xc, xm, m["dilution_centerline"].to_numpy())

    rD = np.log(np.maximum(di, 1e-9) / np.maximum(dc, 1e-9))
    rz = (zi-zc) / max(case.water_depth_m, 1.0)
    return np.concatenate([dilution_weight*rD, trajectory_weight*rz])


def calibrate(cases_csv: str, profiles_dir: str, out_json: str) -> Dict:
    cases_df = pd.read_csv(cases_csv)
    datasets: List[Tuple] = []
    for _, row in cases_df.iterrows():
        cid = str(row["case_id"])
        path = Path(profiles_dir) / f"{cid}.csv"
        if path.exists():
            datasets.append((case_from_row(row), load_profile(path)))

    if not datasets:
        raise ValueError(
            f"No matching profile files found in {profiles_dir}. "
            "Expected <case_id>.csv files."
        )

    base = CalibrationParams()

    # Fit the four parameters most defensible to tune against CORMIX.
    # Bounds deliberately keep parameters near literature/engineering values.
    # x = [alpha_scale, centerline_ratio_asymptote, crossflow_entrainment, drag_coefficient]
    x0 = np.array([
        base.alpha_scale,
        base.centerline_ratio_asymptote,
        base.crossflow_entrainment,
        base.drag_coefficient
    ])
    lo = np.array([0.70, 1.20, 0.10, 0.50])
    hi = np.array([1.30, 2.20, 1.00, 2.50])

    def unpack(x):
        return replace(
            base,
            alpha_scale=float(x[0]),
            centerline_ratio_asymptote=float(x[1]),
            crossflow_entrainment=float(x[2]),
            drag_coefficient=float(x[3]),
        )

    def objective(x):
        cal = unpack(x)
        rr = []
        for case, profile in datasets:
            rr.append(residual_vector(case, profile, cal))
        # Light regularization discourages compensating errors by pushing parameters
        # to bounds when the CORMIX dataset is sparse.
        reg = 0.15 * (x-x0) / np.array([0.20, 0.40, 0.30, 0.70])
        return np.concatenate(rr + [reg])

    fit = least_squares(objective, x0, bounds=(lo, hi), max_nfev=120)
    cal = unpack(fit.x)

    metrics = {}
    for case, profile in datasets:
        metrics[case.case_id] = comparison_metrics(simulate(case, cal=cal), profile)

    payload = {
        "success": bool(fit.success),
        "message": fit.message,
        "n_cases": len(datasets),
        "cost": float(fit.cost),
        "parameters": {
            "alpha_scale": cal.alpha_scale,
            "centerline_ratio_asymptote": cal.centerline_ratio_asymptote,
            "crossflow_entrainment": cal.crossflow_entrainment,
            "drag_coefficient": cal.drag_coefficient,
        },
        "bounds": {
            "alpha_scale": [float(lo[0]), float(hi[0])],
            "centerline_ratio_asymptote": [float(lo[1]), float(hi[1])],
            "crossflow_entrainment": [float(lo[2]), float(hi[2])],
            "drag_coefficient": [float(lo[3]), float(hi[3])],
        },
        "case_metrics": metrics,
        "warning": (
            "Calibration to CORMIX improves agreement with one reference model; it does not "
            "constitute physical validation. Hold back independent cases and compare against "
            "PLUMES2.0 and/or published experiments."
        )
    }
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(payload, indent=2))
    return payload


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("compare")
    p.add_argument("--cases", required=True)
    p.add_argument("--case-id", required=True)
    p.add_argument("--cormix", required=True)
    p.add_argument("--plot", required=True)

    p = sub.add_parser("calibrate")
    p.add_argument("--cases", required=True)
    p.add_argument("--profiles-dir", required=True)
    p.add_argument("--out", required=True)

    args = ap.parse_args()

    if args.command == "compare":
        case = load_case(args.cases, args.case_id)
        cp = load_profile(args.cormix)
        result = simulate(case)
        plot_case(result, args.plot, cp)
        print(json.dumps(comparison_metrics(result, cp), indent=2))
    else:
        payload = calibrate(args.cases, args.profiles_dir, args.out)
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
