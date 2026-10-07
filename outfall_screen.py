#!/usr/bin/env python3
"""
outfall_screen.py

Fast engineering screening model for a single submerged thermal outfall.

Purpose
-------
This is NOT a permitting model and is NOT a replacement for CORMIX/CorJet,
PLUMES2.0/UM3, CFD, or a site-specific hydrodynamic model.

It is intended to answer a narrower concept-design question:

    "Can a simple submerged single pipe generate enough initial dilution
     by jet/plume entrainment, with margin, before boundaries or ambient
     oceanography become essential?"

Model basis
-----------
* Steady, round, top-hat integral jet/plume.
* Conservation of volume, 3-D vector momentum, temperature and salinity.
* Entrainment closure inspired by Jirka/CorJet:
    Gaussian alpha_jet = 0.055
    Gaussian plume increment coefficient = 0.6
    limiting local plume Froude number ~= 4.66
  converted to an approximate top-hat coefficient by sqrt(2).
* Optional forced entrainment and drag from ambient crossflow.
* UNESCO/EOS-80 sigma-t density at atmospheric pressure.
* Near-field only. No atmospheric heat loss and no far-field diffusion.
* Simple linear ambient T/S stratification may be represented.
* Stops on surface, bottom, horizontal-clearance, neutral buoyancy,
  or maximum modeled path length.

Calibration philosophy
-----------------------
The closure coefficients are exposed in CalibrationParams.
When comparing against CORMIX/CorJet, the primary knobs are:
    1) alpha_scale                 -> bulk dilution rate
    2) centerline_ratio_asymptote -> bulk/centerline dilution mapping
    3) crossflow_entrainment      -> dilution in crossflow
    4) drag_coefficient           -> trajectory bending in crossflow

Avoid tuning density, gravity, or conservation equations.

References
----------
Jirka, G.H. (2004), Integral Model for Turbulent Buoyant Jets in Unbounded
Stratified Flows. Part I: Single Round Jet, Environmental Fluid Mechanics 4, 1-56.
CORMIX manuals / CorJet documentation.
US EPA (2024), PLUMES2.0 Dilution Model: Model Theory and User Manual.
UNESCO (1983) / EOS-80 seawater density polynomial.

Usage examples
--------------
python outfall_screen.py run --flow 4000 --diameter 0.8 --sea-temp 20 --delta-t 10 \
    --depth 15 --port-height 1.0 --plot example_outputs/baseline.png

python outfall_screen.py batch test_cases.csv --out example_outputs/test_results.csv \
    --plots example_outputs/plots

python outfall_screen.py envelope --flow 4000 --diameter 0.8 --delta-t 10 \
    --depth 15 --port-height 1.0 --out example_outputs/global_envelope.csv

All lengths are m, velocities m/s, flow input m3/h, temperatures degC,
salinity PSU (numerically close to g/kg for this screening purpose).
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from typing import Optional, Dict, Tuple, List, Any

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

G = 9.80665
CP_SEAWATER = 3990.0  # J/(kg K), adequate engineering value for heat-load display


@dataclass
class OutfallCase:
    # Source
    flow_m3h: float
    diameter_m: float
    sea_temp_C: float
    delta_T_C: float

    # Ambient / effluent salinity
    sea_salinity_psu: float = 35.0
    discharge_salinity_psu: Optional[float] = None

    # Geometry
    water_depth_m: float = 15.0
    port_height_m: float = 1.0
    vertical_angle_deg: float = 0.0
    horizontal_clearance_m: float = 100.0

    # Ambient current. Direction is measured relative to the outlet plan direction:
    # 0 = co-flow, 90 = crossflow, 180 = counterflow.
    current_mps: float = 0.0
    current_direction_deg: float = 90.0

    # Linear ambient stratification, expressed with z positive upward.
    # Example: +0.2 C/m means water is warmer upward.
    temp_gradient_C_per_m: float = 0.0
    salinity_gradient_psu_per_m: float = 0.0

    # Screening criterion
    allowed_delta_T_C: float = 1.0
    design_dilution_factor: float = 1.5

    # Numerical domain
    max_path_m: float = 500.0

    # Optional label
    case_id: str = "case"

    def normalized(self) -> "OutfallCase":
        ds = self.discharge_salinity_psu
        if ds is None or (isinstance(ds, float) and np.isnan(ds)):
            ds = self.sea_salinity_psu
        return replace(self, discharge_salinity_psu=float(ds))


@dataclass
class CalibrationParams:
    # CorJet/Jirka-inspired Gaussian entrainment values.
    alpha_jet_gaussian: float = 0.055
    alpha_plume_increment_gaussian: float = 0.6
    plume_froude_floor: float = 4.66

    # Approximate Gaussian -> top-hat conversion used by JETLAG-like formulations.
    gaussian_to_tophat: float = math.sqrt(2.0)

    # Original screening defaults kept for reference:
    # alpha_scale: float = 1.0
    # centerline_ratio_asymptote: float = 1.7
    #
    # User-case calibration working point for a stagnant 3000 m3/h, DN800,
    # ~18.5 m depth, no-current screening scenario. This deliberately slows the
    # dilution growth to match the expected order of magnitude from the
    # 4 C / 3 C / 2 C mixing-zone screening checks, while keeping the original
    # values as a comment trail for rollback.
    alpha_scale: float = 0.35

    # Forced entrainment by crossflow; Jirka/CorJet uses a coefficient of order 0.5.
    crossflow_entrainment: float = 0.5

    # Crossflow trajectory bending.
    drag_coefficient: float = 1.3

    # CORMIX states bulk dilution Sf is approximately 1.7 x centerline dilution Sc
    # for point/surface discharges in established jet/plume flow. A slightly higher
    # asymptote (2.0) keeps the centerline criterion closer to the historical
    # PLUMES-like trend for these stagnant screening cases.
    centerline_ratio_asymptote: float = 2.0

    # Smooth development of the centerline correction from 1.0 at nozzle to asymptote.
    centerline_development_D: float = 8.0

    # Numerical controls / guards
    min_speed_mps: float = 1e-4
    min_radius_m: float = 1e-4
    max_alpha_tophat: float = 0.20


@dataclass
class ScreeningRules:
    # "Garden hose" GREEN requires design dilution before this fraction of
    # available near-field path to the terminating boundary.
    green_boundary_fraction: float = 0.60

    # Geometry checks used to avoid applying the unbounded-round-jet model in a
    # clearly boundary-dominated source region.
    minimum_port_height_over_D: float = 1.0

    # CORMIX1 traditional geometry applicability reminders for near-horizontal ports.
    cormix_port_height_fraction_depth: float = 1.0 / 3.0
    cormix_horizontal_D_fraction_depth: float = 1.0 / 3.0

    # If ambient current is a large fraction of exit speed, crossflow closure matters strongly.
    strong_current_ratio: float = 0.50


def seawater_density_eos80(temp_C: float | np.ndarray,
                           salinity_psu: float | np.ndarray) -> float | np.ndarray:
    """
    UNESCO 1983 / EOS-80 density at atmospheric pressure (kg/m3).

    This is the standard sigma-t style polynomial used in many legacy marine
    mixing models. Pressure/compressibility is omitted because plume and ambient
    are compared at approximately the same local depth; for this screening model
    the density DIFFERENCE is the key quantity.
    """
    T = np.asarray(temp_C, dtype=float)
    S = np.maximum(np.asarray(salinity_psu, dtype=float), 0.0)

    rho_w = (
        999.842594
        + 6.793952e-2 * T
        - 9.095290e-3 * T**2
        + 1.001685e-4 * T**3
        - 1.120083e-6 * T**4
        + 6.536332e-9 * T**5
    )
    A = (
        0.824493
        - 4.0899e-3 * T
        + 7.6438e-5 * T**2
        - 8.2467e-7 * T**3
        + 5.3875e-9 * T**4
    )
    B = -5.72466e-3 + 1.0227e-4 * T - 1.6546e-6 * T**2
    C = 4.8314e-4
    rho = rho_w + A * S + B * S**1.5 + C * S**2
    if np.ndim(rho) == 0:
        return float(rho)
    return rho


def ambient_properties(case: OutfallCase, z_m: float) -> Tuple[float, float, float]:
    """Ambient T, S, rho at elevation z above seabed; gradients referenced to outlet elevation."""
    z = float(np.clip(z_m, 0.0, case.water_depth_m))
    dz = z - case.port_height_m
    T = case.sea_temp_C + case.temp_gradient_C_per_m * dz
    S = case.sea_salinity_psu + case.salinity_gradient_psu_per_m * dz
    S = max(S, 0.0)
    rho = seawater_density_eos80(T, S)
    return T, S, rho


def source_properties(case: OutfallCase) -> Dict[str, float]:
    case = case.normalized()
    Q0 = case.flow_m3h / 3600.0
    area0 = math.pi * case.diameter_m**2 / 4.0
    U0 = Q0 / area0
    T0 = case.sea_temp_C + case.delta_T_C
    S0 = float(case.discharge_salinity_psu)
    rho_a0 = seawater_density_eos80(case.sea_temp_C, case.sea_salinity_psu)
    rho_0 = seawater_density_eos80(T0, S0)
    gprime0 = G * (rho_a0 - rho_0) / rho_a0
    M0 = Q0 * U0
    J0 = gprime0 * Q0

    if abs(gprime0) > 1e-12:
        Fr0 = U0 / math.sqrt(abs(gprime0) * case.diameter_m)
    else:
        Fr0 = math.inf

    if abs(J0) > 1e-15:
        LM = M0**0.75 / math.sqrt(abs(J0))
    else:
        LM = math.inf

    LQ = Q0 / math.sqrt(M0) if M0 > 0 else math.nan
    Ua = case.current_mps
    Lm = math.sqrt(M0) / Ua if Ua > 0 else math.inf
    Lb = abs(J0) / Ua**3 if Ua > 0 else math.inf
    heat_MW = rho_0 * Q0 * CP_SEAWATER * case.delta_T_C / 1e6

    return {
        "Q0_m3s": Q0,
        "area0_m2": area0,
        "velocity0_mps": U0,
        "discharge_temp_C": T0,
        "discharge_salinity_psu": S0,
        "rho_ambient0_kgm3": rho_a0,
        "rho_discharge_kgm3": rho_0,
        "delta_rho0_kgm3": rho_a0 - rho_0,
        "gprime0_mps2": gprime0,
        "momentum_flux_M0_m4s2": M0,
        "buoyancy_flux_J0_m4s3": J0,
        "Fr0": Fr0,
        "LM_m": LM,
        "LQ_m": LQ,
        "Lm_current_m": Lm,
        "Lb_current_m": Lb,
        "heat_rejection_MW": heat_MW,
        "submergence_center_m": case.water_depth_m - case.port_height_m,
        "submergence_over_D": (case.water_depth_m - case.port_height_m) / case.diameter_m,
        "port_height_over_D": case.port_height_m / case.diameter_m,
        "water_depth_over_D": case.water_depth_m / case.diameter_m,
        "required_dilution": case.delta_T_C / case.allowed_delta_T_C,
        "green_design_dilution": (
            case.delta_T_C / case.allowed_delta_T_C * case.design_dilution_factor
        ),
    }


def _velocity_vectors(case: OutfallCase, U0: float) -> Tuple[np.ndarray, np.ndarray]:
    th = math.radians(case.vertical_angle_deg)
    v0 = np.array([U0 * math.cos(th), 0.0, U0 * math.sin(th)], dtype=float)

    psi = math.radians(case.current_direction_deg)
    ua = np.array([
        case.current_mps * math.cos(psi),
        case.current_mps * math.sin(psi),
        0.0
    ], dtype=float)
    return v0, ua


def _derived_at_state(s: float, y: np.ndarray, case: OutfallCase,
                      cal: CalibrationParams, source: Dict[str, float]) -> Dict[str, float]:
    x, yy, z, Q, Px, Py, Pz, heat_flux, salt_flux = y
    Q = max(Q, 1e-12)
    P = np.array([Px, Py, Pz], dtype=float)
    V = P / Q
    speed = max(float(np.linalg.norm(V)), cal.min_speed_mps)
    tvec = V / speed
    area = Q / speed
    b = max(math.sqrt(max(area, 1e-12) / math.pi), cal.min_radius_m)

    Tj = heat_flux / Q
    Sj = max(salt_flux / Q, 0.0)
    Ta, Sa, rho_a = ambient_properties(case, z)
    rho_j = seawater_density_eos80(Tj, Sj)
    gprime = G * (rho_a - rho_j) / rho_a

    _, Ua = _velocity_vectors(case, source["velocity0_mps"])
    Ua_t = float(np.dot(Ua, tvec))
    Ua_perp_vec = Ua - Ua_t * tvec
    Ua_perp = float(np.linalg.norm(Ua_perp_vec))
    axial_rel = max(speed - Ua_t, 0.0)

    # Local CorJet/Jirka-inspired shear entrainment.
    if abs(gprime) > 1e-12:
        Fl = axial_rel / math.sqrt(abs(gprime) * b)
    else:
        Fl = math.inf

    buoyancy_alignment = max(0.0, math.copysign(1.0, gprime) * float(tvec[2])) if abs(gprime) > 1e-12 else 0.0
    Fr_eff = max(Fl, cal.plume_froude_floor)
    alpha_gauss = (
        cal.alpha_jet_gaussian
        + cal.alpha_plume_increment_gaussian * buoyancy_alignment / (Fr_eff**2)
    )
    alpha_tophat = cal.gaussian_to_tophat * alpha_gauss * cal.alpha_scale
    alpha_tophat = min(max(alpha_tophat, 0.0), cal.max_alpha_tophat)

    dQds_shear = 2.0 * math.pi * b * alpha_tophat * axial_rel
    dQds_forced = cal.crossflow_entrainment * 2.0 * b * Ua_perp
    dQds = max(dQds_shear + dQds_forced, 0.0)

    dilution_bulk = Q / source["Q0_m3s"]

    ratio = 1.0 + (cal.centerline_ratio_asymptote - 1.0) * (
        1.0 - math.exp(-max(s, 0.0) / max(cal.centerline_development_D * case.diameter_m, 1e-9))
    )
    dilution_centerline = dilution_bulk / ratio

    theta = math.degrees(math.asin(np.clip(tvec[2], -1.0, 1.0)))

    return {
        "x_m": x,
        "y_m": yy,
        "z_m": z,
        "Q_m3s": Q,
        "speed_mps": speed,
        "vx_mps": V[0],
        "vy_mps": V[1],
        "vz_mps": V[2],
        "radius_m": b,
        "diameter_plume_m": 2.0 * b,
        "plume_temp_C": Tj,
        "plume_salinity_psu": Sj,
        "ambient_temp_C": Ta,
        "ambient_salinity_psu": Sa,
        "plume_density_kgm3": rho_j,
        "ambient_density_kgm3": rho_a,
        "gprime_mps2": gprime,
        "local_Froude": Fl,
        "alpha_tophat": alpha_tophat,
        "dQds_shear_m2s": dQds_shear,
        "dQds_forced_m2s": dQds_forced,
        "dQds_total_m2s": dQds,
        "dilution_bulk": dilution_bulk,
        "bulk_to_centerline_ratio": ratio,
        "dilution_centerline": dilution_centerline,
        "centerline_delta_T_C": case.delta_T_C / max(dilution_centerline, 1e-12),
        "bulk_delta_T_C": case.delta_T_C / max(dilution_bulk, 1e-12),
        "trajectory_angle_deg": theta,
        "current_perp_mps": Ua_perp,
        "current_tangent_mps": Ua_t,
        "horizontal_distance_m": math.hypot(x, yy),
    }


def simulate(case: OutfallCase,
             cal: Optional[CalibrationParams] = None,
             rules: Optional[ScreeningRules] = None,
             max_step_m: Optional[float] = None) -> Dict[str, Any]:
    case = case.normalized()
    cal = cal or CalibrationParams()
    rules = rules or ScreeningRules()

    _validate_case(case)

    src = source_properties(case)
    Q0 = src["Q0_m3s"]
    U0 = src["velocity0_mps"]
    T0 = src["discharge_temp_C"]
    S0 = src["discharge_salinity_psu"]

    v0, Ua = _velocity_vectors(case, U0)
    P0 = Q0 * v0

    y0 = np.array([
        0.0, 0.0, case.port_height_m,
        Q0,
        P0[0], P0[1], P0[2],
        Q0 * T0,
        Q0 * S0
    ], dtype=float)

    gprime_sign0 = 1.0 if src["gprime0_mps2"] >= 0 else -1.0

    def rhs(s: float, y: np.ndarray) -> np.ndarray:
        d = _derived_at_state(s, y, case, cal, src)
        Q = max(y[3], 1e-12)
        P = y[4:7]
        V = P / Q
        speed = max(float(np.linalg.norm(V)), cal.min_speed_mps)
        tvec = V / speed

        dQds = d["dQds_total_m2s"]
        b = d["radius_m"]
        area = Q / speed

        # Momentum carried by entrained ambient water.
        dP = Ua * dQds

        # Buoyancy force per unit path length.
        dP += np.array([0.0, 0.0, d["gprime_mps2"] * area])

        # Crossflow drag, CorJet-style engineering closure.
        Ua_t = float(np.dot(Ua, tvec))
        Ua_perp_vec = Ua - Ua_t * tvec
        Ua_perp = float(np.linalg.norm(Ua_perp_vec))
        if Ua_perp > 1e-12:
            drag_mag = 0.5 * cal.drag_coefficient * (2.0 * b) * Ua_perp**2
            dP += drag_mag * Ua_perp_vec / Ua_perp

        Ta, Sa, _ = ambient_properties(case, y[2])

        dy = np.zeros_like(y)
        dy[0:3] = tvec
        dy[3] = dQds
        dy[4:7] = dP
        dy[7] = Ta * dQds
        dy[8] = Sa * dQds
        return dy

    def surface_event(s, y):
        d = _derived_at_state(s, y, case, cal, src)
        return case.water_depth_m - (y[2] + d["radius_m"])

    def bottom_event(s, y):
        d = _derived_at_state(s, y, case, cal, src)
        # Ignore the exact nozzle edge contact in the first fraction of a diameter.
        if s < 0.25 * case.diameter_m:
            return max(y[2] - d["radius_m"], 1e-6)
        return y[2] - d["radius_m"]

    def clearance_event(s, y):
        d = _derived_at_state(s, y, case, cal, src)
        return case.horizontal_clearance_m - (d["horizontal_distance_m"] + d["radius_m"])

    def neutral_event(s, y):
        d = _derived_at_state(s, y, case, cal, src)
        return gprime_sign0 * d["gprime_mps2"]

    for ev in (surface_event, bottom_event, clearance_event, neutral_event):
        ev.terminal = True
        ev.direction = -1

    if max_step_m is None:
        max_step_m = max(0.05, min(case.diameter_m / 5.0, case.max_path_m / 1000.0))

    sol = solve_ivp(
        rhs,
        (0.0, case.max_path_m),
        y0,
        events=[surface_event, bottom_event, clearance_event, neutral_event],
        rtol=1e-7,
        atol=1e-9,
        max_step=max_step_m,
        dense_output=False,
    )

    event_names = ["surface", "bottom", "horizontal_clearance", "neutral_buoyancy"]
    termination = "max_path"
    event_s = float(sol.t[-1])
    for name, te in zip(event_names, sol.t_events):
        if len(te):
            termination = name
            event_s = float(te[0])
            break

    rows: List[Dict[str, float]] = []
    for s, y in zip(sol.t, sol.y.T):
        row = {"s_m": float(s)}
        row.update(_derived_at_state(float(s), y, case, cal, src))
        rows.append(row)
    df = pd.DataFrame(rows)

    summary = _screen_summary(case, src, df, termination, event_s, cal, rules)
    summary["solver_success"] = bool(sol.success)
    summary["solver_message"] = sol.message
    summary["case_id"] = case.case_id

    return {
        "case": asdict(case),
        "calibration": asdict(cal),
        "rules": asdict(rules),
        "source": src,
        "summary": summary,
        "profile": df,
    }


def _screen_summary(case: OutfallCase, src: Dict[str, float], df: pd.DataFrame,
                    termination: str, event_s: float,
                    cal: CalibrationParams, rules: ScreeningRules) -> Dict[str, Any]:
    req = src["required_dilution"]
    green_req = src["green_design_dilution"]

    def first_crossing(column: str, target: float) -> Optional[Dict[str, float]]:
        vals = df[column].to_numpy()
        idx = np.where(vals >= target)[0]
        if not len(idx):
            return None
        i = int(idx[0])
        return df.iloc[i].to_dict()

    p_req = first_crossing("dilution_centerline", req)
    p_green = first_crossing("dilution_centerline", green_req)
    end = df.iloc[-1].to_dict()

    warnings: List[str] = []
    h_over_d = case.port_height_m / case.diameter_m
    if h_over_d < rules.minimum_port_height_over_D:
        warnings.append(
            f"Port center height/D = {h_over_d:.2f} < "
            f"{rules.minimum_port_height_over_D:.2f}; bottom interaction may invalidate an unbounded jet model."
        )
    if case.port_height_m > rules.cormix_port_height_fraction_depth * case.water_depth_m:
        warnings.append(
            "Port center is above one-third of local depth; outside the traditional CORMIX1 "
            "submerged-port geometry check used in older manuals."
        )
    if abs(case.vertical_angle_deg) <= 45 and case.diameter_m > (
        rules.cormix_horizontal_D_fraction_depth * case.water_depth_m
    ):
        warnings.append(
            "Port diameter exceeds one-third of local depth for a near-horizontal outlet; "
            "strong boundary effects are likely."
        )
    current_ratio = case.current_mps / max(src["velocity0_mps"], 1e-12)
    if current_ratio > rules.strong_current_ratio:
        warnings.append(
            f"Ambient current/exit velocity = {current_ratio:.2f}; crossflow physics are strong "
            "and should be checked directly in CORMIX/PLUMES."
        )
    if abs(case.temp_gradient_C_per_m) > 0 or abs(case.salinity_gradient_psu_per_m) > 0:
        warnings.append(
            "Stratification is active; this simplified linear-profile treatment should be verified "
            "against CORMIX/PLUMES for design use."
        )

    margin_fraction = None
    if p_green is not None and event_s > 0:
        margin_fraction = float(p_green["s_m"]) / event_s

    if p_req is None:
        status = "RED"
        reason = (
            f"Centerline dilution never reaches required {req:.2f}:1 before "
            f"{termination}; final centerline dilution is {end['dilution_centerline']:.2f}:1."
        )
    elif p_green is None:
        status = "AMBER"
        reason = (
            f"Required dilution {req:.2f}:1 is reached, but the design target "
            f"{green_req:.2f}:1 is not reached before {termination}."
        )
    elif margin_fraction is not None and margin_fraction > rules.green_boundary_fraction:
        status = "AMBER"
        reason = (
            f"Design dilution is reached, but only after {100*margin_fraction:.0f}% of the available "
            "near-field path; boundary margin is small."
        )
    elif warnings:
        status = "AMBER"
        reason = (
            "Dilution target is reached with path margin, but applicability warnings remain; "
            "verify the flagged physics in CORMIX/PLUMES."
        )
    else:
        status = "GREEN"
        reason = (
            "Design centerline dilution is reached with geometric/path margin before any modeled "
            "near-field termination boundary."
        )

    momentum_dominated_at_req = None
    if p_req is not None and np.isfinite(src["LM_m"]):
        momentum_dominated_at_req = float(p_req["s_m"]) < src["LM_m"]

    return {
        "status": status,
        "reason": reason,
        "termination": termination,
        "termination_s_m": event_s,
        "termination_horizontal_distance_m": float(end["horizontal_distance_m"]),
        "termination_z_m": float(end["z_m"]),
        "termination_centerline_dilution": float(end["dilution_centerline"]),
        "termination_bulk_dilution": float(end["dilution_bulk"]),
        "termination_centerline_delta_T_C": float(end["centerline_delta_T_C"]),
        "required_dilution": req,
        "green_design_dilution": green_req,
        "required_reached_s_m": None if p_req is None else float(p_req["s_m"]),
        "required_reached_horizontal_m": None if p_req is None else float(p_req["horizontal_distance_m"]),
        "required_reached_z_m": None if p_req is None else float(p_req["z_m"]),
        "green_reached_s_m": None if p_green is None else float(p_green["s_m"]),
        "green_reached_horizontal_m": None if p_green is None else float(p_green["horizontal_distance_m"]),
        "green_reached_z_m": None if p_green is None else float(p_green["z_m"]),
        "green_path_fraction": margin_fraction,
        "momentum_dominated_at_required_dilution": momentum_dominated_at_req,
        "warnings": warnings,
    }


def _validate_case(case: OutfallCase) -> None:
    vals = {
        "flow_m3h": case.flow_m3h,
        "diameter_m": case.diameter_m,
        "water_depth_m": case.water_depth_m,
        "allowed_delta_T_C": case.allowed_delta_T_C,
        "max_path_m": case.max_path_m,
        "horizontal_clearance_m": case.horizontal_clearance_m,
    }
    for k, v in vals.items():
        if not np.isfinite(v) or v <= 0:
            raise ValueError(f"{k} must be finite and > 0; got {v}")
    if case.port_height_m <= 0 or case.port_height_m >= case.water_depth_m:
        raise ValueError("port_height_m must be >0 and < water_depth_m")
    if case.delta_T_C <= 0:
        raise ValueError("This v0 screening model is intended for positively buoyant thermal discharges (delta_T_C > 0).")
    if not (-45.0 <= case.vertical_angle_deg <= 90.0):
        raise ValueError("vertical_angle_deg must lie between -45 and 90 degrees.")


def plot_case(result: Dict[str, Any], output_path: str | Path,
              cormix_profile: Optional[pd.DataFrame] = None) -> None:
    """
    Create a 2-panel engineering plot:
      1) side-view centerline trajectory with plume envelope
      2) centerline dilution vs horizontal distance

    If cormix_profile is supplied, expected columns are:
      x_m, z_m, dilution_centerline
    Optional y_m may be included.
    """
    df = result["profile"]
    case = result["case"]
    src = result["source"]
    summ = result["summary"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

    ax = axes[0]
    x = df["horizontal_distance_m"].to_numpy()
    z = df["z_m"].to_numpy()
    b = df["radius_m"].to_numpy()
    ax.plot(x, z, label="Screen model centerline")
    ax.fill_between(x, np.maximum(z-b, 0), np.minimum(z+b, case["water_depth_m"]),
                    alpha=0.16, label="Top-hat plume envelope")
    ax.axhline(case["water_depth_m"], linestyle="--", linewidth=1, label="Water surface")
    ax.axhline(0, linewidth=1)
    if np.isfinite(src["LM_m"]):
        # LM is path length, so mark nearest row in s.
        i = int(np.argmin(np.abs(df["s_m"].to_numpy() - src["LM_m"])))
        ax.scatter([x[i]], [z[i]], s=45, label="Jet/plume scale $L_M$")
    if cormix_profile is not None and {"x_m", "z_m"}.issubset(cormix_profile.columns):
        if "y_m" in cormix_profile.columns:
            cx = np.hypot(cormix_profile["x_m"], cormix_profile["y_m"])
        else:
            cx = cormix_profile["x_m"]
        ax.plot(cx, cormix_profile["z_m"], linestyle="--", label="CORMIX/CorJet")
    ax.set_xlabel("Horizontal distance from outlet (m)")
    ax.set_ylabel("Elevation above seabed (m)")
    ax.set_title(f"{case['case_id']}: plume trajectory")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1]
    ax.plot(x, df["dilution_centerline"], label="Screen centerline dilution")
    ax.plot(x, df["dilution_bulk"], linestyle=":", label="Screen bulk dilution")
    ax.axhline(src["required_dilution"], linestyle="--", linewidth=1, label="Required dilution")
    ax.axhline(src["green_design_dilution"], linestyle="-.", linewidth=1, label="Green design dilution")
    if cormix_profile is not None and {"x_m", "dilution_centerline"}.issubset(cormix_profile.columns):
        if "y_m" in cormix_profile.columns:
            cx = np.hypot(cormix_profile["x_m"], cormix_profile["y_m"])
        else:
            cx = cormix_profile["x_m"]
        ax.plot(cx, cormix_profile["dilution_centerline"], linestyle="--", label="CORMIX/CorJet centerline")
    ax.set_xlabel("Horizontal distance from outlet (m)")
    ax.set_ylabel("Dilution (-)")
    ax.set_title(f"Thermal screen: {summ['status']}")
    ax.set_ylim(bottom=1)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    fig.suptitle(
        f"Q={case['flow_m3h']:.0f} m3/h, D={case['diameter_m']:.2f} m, "
        f"U0={src['velocity0_mps']:.2f} m/s, dT={case['delta_T_C']:.1f} C, "
        f"H={case['water_depth_m']:.1f} m",
        fontsize=11
    )
    fig.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def case_from_row(row: pd.Series) -> OutfallCase:
    field_names = set(OutfallCase.__dataclass_fields__.keys())
    kw = {}
    for k in field_names:
        if k in row.index and not pd.isna(row[k]):
            kw[k] = row[k]
    return OutfallCase(**kw)


def batch_run(csv_path: str | Path, out_csv: str | Path,
              plots_dir: Optional[str | Path] = None,
              cal: Optional[CalibrationParams] = None) -> pd.DataFrame:
    inp = pd.read_csv(csv_path)
    results = []
    for _, row in inp.iterrows():
        case = case_from_row(row)
        res = simulate(case, cal=cal)
        flat = {
            **res["case"],
            **{f"src_{k}": v for k, v in res["source"].items()},
            **{f"result_{k}": v if not isinstance(v, list) else " | ".join(v)
               for k, v in res["summary"].items()},
        }
        results.append(flat)
        if plots_dir:
            p = Path(plots_dir) / f"{case.case_id}.png"
            plot_case(res, p)
    out = pd.DataFrame(results)
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False)
    return out


def run_global_envelope(base: OutfallCase,
                        out_csv: str | Path,
                        cal: Optional[CalibrationParams] = None) -> pd.DataFrame:
    """
    Screening envelope, NOT a proof of universal regulatory compliance.

    Sweeps:
      sea T: 0, 10, 20, 30 C
      salinity: 30, 35, 40 PSU
      current: 0, 0.1, 0.3, 0.5 m/s
      current direction: 0, 90, 180 deg

    Stratification is left at the base-case setting. Use explicit cases for
    stratified checks because realistic gradients are site/climate dependent.
    """
    rows = []
    i = 0
    for T in [0.0, 10.0, 20.0, 30.0]:
        for S in [30.0, 35.0, 40.0]:
            for U in [0.0, 0.1, 0.3, 0.5]:
                dirs = [90.0] if U == 0 else [0.0, 90.0, 180.0]
                for d in dirs:
                    i += 1
                    c = replace(
                        base,
                        case_id=f"env_{i:03d}",
                        sea_temp_C=T,
                        sea_salinity_psu=S,
                        discharge_salinity_psu=S,
                        current_mps=U,
                        current_direction_deg=d,
                    )
                    res = simulate(c, cal=cal)
                    rows.append({
                        "case_id": c.case_id,
                        "sea_temp_C": T,
                        "sea_salinity_psu": S,
                        "current_mps": U,
                        "current_direction_deg": d,
                        "status": res["summary"]["status"],
                        "termination": res["summary"]["termination"],
                        "centerline_dilution_end": res["summary"]["termination_centerline_dilution"],
                        "centerline_delta_T_end_C": res["summary"]["termination_centerline_delta_T_C"],
                        "green_path_fraction": res["summary"]["green_path_fraction"],
                        "velocity0_mps": res["source"]["velocity0_mps"],
                        "Fr0": res["source"]["Fr0"],
                        "LM_m": res["source"]["LM_m"],
                        "warnings": " | ".join(res["summary"]["warnings"]),
                    })
    out = pd.DataFrame(rows)
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False)
    return out


def print_result(result: Dict[str, Any]) -> None:
    src = result["source"]
    s = result["summary"]
    c = result["case"]
    print(f"\n=== {c['case_id']} ===")
    print(f"Status: {s['status']}")
    print(s["reason"])
    print(f"Q = {c['flow_m3h']:.1f} m3/h | D = {c['diameter_m']:.3f} m | U0 = {src['velocity0_mps']:.3f} m/s")
    print(f"Tsea = {c['sea_temp_C']:.1f} C | Tout = {src['discharge_temp_C']:.1f} C | dT = {c['delta_T_C']:.1f} C")
    print(f"rho_a = {src['rho_ambient0_kgm3']:.3f} kg/m3 | rho_0 = {src['rho_discharge_kgm3']:.3f} kg/m3")
    print(f"g' = {src['gprime0_mps2']:.5f} m/s2 | Fr0 = {src['Fr0']:.2f} | LM = {src['LM_m']:.2f} m")
    print(f"Submergence/D = {src['submergence_over_D']:.2f} | H/D = {src['water_depth_over_D']:.2f}")
    print(f"Heat rejection = {src['heat_rejection_MW']:.2f} MW")
    print(f"Required dilution = {src['required_dilution']:.2f}:1 | Green target = {src['green_design_dilution']:.2f}:1")
    print(f"Termination = {s['termination']} at s={s['termination_s_m']:.2f} m, horizontal={s['termination_horizontal_distance_m']:.2f} m")
    print(f"End centerline dilution = {s['termination_centerline_dilution']:.2f}:1 | dT_centerline={s['termination_centerline_delta_T_C']:.3f} C")
    if s["warnings"]:
        print("Warnings:")
        for w in s["warnings"]:
            print(" -", w)


def _case_from_args(a: argparse.Namespace) -> OutfallCase:
    return OutfallCase(
        flow_m3h=a.flow,
        diameter_m=a.diameter,
        sea_temp_C=a.sea_temp,
        delta_T_C=a.delta_t,
        sea_salinity_psu=a.salinity,
        discharge_salinity_psu=a.discharge_salinity,
        water_depth_m=a.depth,
        port_height_m=a.port_height,
        vertical_angle_deg=a.angle,
        horizontal_clearance_m=a.clearance,
        current_mps=a.current,
        current_direction_deg=a.current_direction,
        temp_gradient_C_per_m=a.temp_gradient,
        salinity_gradient_psu_per_m=a.salinity_gradient,
        allowed_delta_T_C=a.allowed_delta_t,
        design_dilution_factor=a.design_factor,
        max_path_m=a.max_path,
        case_id=a.case_id,
    )


def add_case_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--flow", type=float, required=True, help="Discharge flow m3/h")
    p.add_argument("--diameter", type=float, required=True, help="Port internal diameter m")
    p.add_argument("--sea-temp", type=float, default=20.0, help="Ambient temperature at outlet elevation C")
    p.add_argument("--delta-t", type=float, default=10.0, help="Process temperature rise C")
    p.add_argument("--salinity", type=float, default=35.0, help="Ambient salinity PSU")
    p.add_argument("--discharge-salinity", type=float, default=None, help="Effluent salinity PSU; default=same as ambient")
    p.add_argument("--depth", type=float, required=True, help="Local water depth m")
    p.add_argument("--port-height", type=float, required=True, help="Port center height above seabed m")
    p.add_argument("--angle", type=float, default=0.0, help="Vertical outlet angle above horizontal deg")
    p.add_argument("--clearance", type=float, default=100.0, help="Horizontal clearance to first boundary/receptor m")
    p.add_argument("--current", type=float, default=0.0, help="Ambient current speed m/s")
    p.add_argument("--current-direction", type=float, default=90.0, help="Current direction relative to outlet plan axis deg")
    p.add_argument("--temp-gradient", type=float, default=0.0, help="Ambient dT/dz C/m, z positive upward")
    p.add_argument("--salinity-gradient", type=float, default=0.0, help="Ambient dS/dz PSU/m, z positive upward")
    p.add_argument("--allowed-delta-t", type=float, default=1.0, help="Thermal rise screening criterion C")
    p.add_argument("--design-factor", type=float, default=1.5, help="Dilution safety/design factor")
    p.add_argument("--max-path", type=float, default=500.0, help="Maximum near-field path length m")
    p.add_argument("--case-id", default="case")


def main() -> None:
    ap = argparse.ArgumentParser(description="Submerged thermal outfall screening model")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="Run one case")
    add_case_args(p)
    p.add_argument("--plot", help="PNG output path")
    p.add_argument("--profile-csv", help="Save full model profile CSV")
    p.add_argument("--json", dest="json_out", help="Save summary JSON")

    p = sub.add_parser("batch", help="Run cases from CSV")
    p.add_argument("csv")
    p.add_argument("--out", required=True)
    p.add_argument("--plots", help="Directory for plots")

    p = sub.add_parser("envelope", help="Run global T/S/current screening envelope")
    add_case_args(p)
    p.add_argument("--out", required=True)

    args = ap.parse_args()

    if args.command == "run":
        case = _case_from_args(args)
        res = simulate(case)
        print_result(res)
        if args.plot:
            plot_case(res, args.plot)
        if args.profile_csv:
            Path(args.profile_csv).parent.mkdir(parents=True, exist_ok=True)
            res["profile"].to_csv(args.profile_csv, index=False)
        if args.json_out:
            Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
            serial = {k: v for k, v in res.items() if k != "profile"}
            Path(args.json_out).write_text(json.dumps(serial, indent=2, default=str))
    elif args.command == "batch":
        out = batch_run(args.csv, args.out, args.plots)
        print(out[["case_id", "result_status", "result_termination",
                   "result_termination_centerline_dilution"]].to_string(index=False))
    elif args.command == "envelope":
        case = _case_from_args(args)
        out = run_global_envelope(case, args.out)
        print(out.groupby("status").size().to_string())
        worst = out.sort_values("centerline_dilution_end").head(10)
        print("\nLowest terminal centerline dilution cases:")
        print(worst[["case_id", "sea_temp_C", "sea_salinity_psu", "current_mps",
                     "current_direction_deg", "status", "centerline_dilution_end"]].to_string(index=False))


if __name__ == "__main__":
    main()
