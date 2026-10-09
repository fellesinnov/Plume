"""Headless DESIGN-1: one pinned water column -> actual MODEL-1/FIELD-1 outputs.

No provider/network or Streamlit imports in this module. Metrics describe discrete
near-field *slices*, not 3-D permit compliance or validated thermal footprints.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from ..config import normalize_config
from ..errors import ModelInputError, ProviderDataError
from ..field import FieldSlice, horizontal_plan, vertical_section
from ..model import (
    AmbientColumn, AmbientLevel, GswThermodynamics, NearFieldOptions,
    NearFieldProblem, NearFieldSolution, SourceState, build_near_field_port,
    solve_near_field,
)
from ..model.thermodynamics import Thermodynamics
from .snapshot import PinnedSnapshot, _digest


@dataclass(frozen=True)
class DesignEvaluation:
    normalized_config: dict[str, Any]
    config_sha256: str
    snapshot: PinnedSnapshot
    solution: NearFieldSolution
    section: FieldSlice
    plan: FieldSlice
    metrics: dict[str, Any]

    def record(self) -> dict[str, Any]:
        return {
            "snapshot_sha256": self.snapshot.snapshot_sha256,
            "config_sha256": self.config_sha256,
            "metrics": self.metrics,
            "qualification": "UNVALIDATED; near-field slice indicators only, not permit verdicts",
        }


def candidate_config(base: Mapping[str, Any], *, depth_m: float, diameter_m: float,
                     angle_deg: float, azimuth_deg: float, flow_m3h: float,
                     discharge_temperature_C: float | None = None,
                     delta_T_C: float | None = None) -> dict[str, Any]:
    """Modify *only* supported geometry/plant controls in schema-v1 config."""
    if (discharge_temperature_C is None) == (delta_T_C is None):
        raise ModelInputError("choose exactly one absolute discharge temperature or process delta_T")
    raw = copy.deepcopy(dict(base))
    if raw["outfall"]["type"] != "single_round_port":
        raise ModelInputError("DESIGN-1 supports only the single_round_port model")
    raw["outfall"].update({
        "discharge_depth_below_surface_m": depth_m,
        "diameter_m": diameter_m,
        "vertical_angle_deg": angle_deg,
        "azimuth_deg": azimuth_deg,
    })
    raw["forcing"]["source"]["flow_m3h"] = {"provider": "constant", "value": flow_m3h}
    raw["forcing"]["source"].pop("delta_T_C", None)
    raw["forcing"]["source"].pop("discharge_temperature_C", None)
    key = "delta_T_C" if delta_T_C is not None else "discharge_temperature_C"
    val = delta_T_C if delta_T_C is not None else discharge_temperature_C
    raw["forcing"]["source"][key] = {"provider": "constant", "value": val}
    return normalize_config(raw)


def _candidate_scalar(name: str, normalized: Mapping[str, Any], snapshot: PinnedSnapshot) -> float:
    spec = normalized["forcing"]["source"][name]
    if spec["provider"] == "constant":
        val = float(spec["value"])
    elif name in snapshot.source_specs and spec == snapshot.source_specs[name]:
        val = snapshot.source_scalars[name]
    else:
        raise ProviderDataError(f"{name}: changed file/provider source requires repinning, or use constant design controls")
    if not math.isfinite(val):
        raise ModelInputError(f"{name}: value is not finite")
    return val


def _threshold(normalized: Mapping[str, Any]) -> float:
    values = [float(c["threshold_delta_T_C"]) for c in normalized["criteria"]
              if c["type"] == "isotherm_extent" and "threshold_delta_T_C" in c]
    value = values[0] if values else 2.0
    if not math.isfinite(value) or value <= 0:
        raise ModelInputError("isotherm threshold must be positive and finite")
    return value


def sampled_isotherm_indicators(section: FieldSlice, plan: FieldSlice, *,
                               threshold_delta_T_C: float) -> dict[str, float | bool | None]:
    """Measure a selected ΔT isotherm on existing MODEL/FIELD slices only.

    Results are grid-sampled near-field indicators, not continuous 3-D extents,
    validated physics, far-field outcomes or permit-compliance verdicts.
    None means no above-threshold sample *in this slice*, not no warming.
    """
    level = float(threshold_delta_T_C)
    if not math.isfinite(level) or level <= 0:
        raise ModelInputError("display isotherm threshold must be positive and finite")
    if section.plane != "section" or plan.plane != "plan":
        raise ModelInputError("requires physical section and plan slices")
    sec_mask = section.values.modeled & (section.values.delta_temperature_C >= level)
    plan_mask = plan.values.modeled & (plan.values.delta_temperature_C >= level)
    sec_x, _ = np.meshgrid(section.horizontal_axis_m, section.vertical_axis_m)
    plan_x, plan_y = np.meshgrid(plan.horizontal_axis_m, plan.vertical_axis_m)
    cell_area = (float(np.diff(plan.horizontal_axis_m).mean()) *
                 float(np.diff(plan.vertical_axis_m).mean()))
    clipped = bool(any(np.any(edge) for mask in (sec_mask, plan_mask)
                       for edge in (mask[0, :], mask[-1, :],
                                    mask[:, 0], mask[:, -1])))
    return {
        "threshold_delta_T_C": level,
        "section_threshold_max_distance_m":
            float(np.max(sec_x[sec_mask])) if sec_mask.any() else None,
        "plan_threshold_farthest_radius_m":
            float(np.max(np.hypot(plan_x[plan_mask], plan_y[plan_mask]))) if plan_mask.any() else None,
        "plan_threshold_sampled_area_m2": float(np.count_nonzero(plan_mask) * cell_area),
        "grid_boundary_threshold_contact": clipped,
    }


def evaluate_design(candidate: Mapping[str, Any], snapshot: PinnedSnapshot, *,
                    thermodynamics: Thermodynamics | None = None,
                    section_resolution: tuple[int, int] = (101, 71),
                    plan_resolution: tuple[int, int] = (101, 71)) -> DesignEvaluation:
    """Evaluate one candidate without loading or mutating any provider/cache.

    Uses *exactly* MODEL-1 solve_near_field and FIELD-1 slices; the evaluation
    only picks physical view grids and derives bounded slice-level indicators.
    """
    snapshot.verify_identity()
    normalized = normalize_config(candidate)
    if normalized["site"] != snapshot.site or _digest(normalized["forcing"]["ambient"]) != snapshot.ambient_spec_sha256:
        raise ProviderDataError("site or ambient provider changed; repin environmental snapshot")
    if normalized["outfall"]["type"] != "single_round_port":
        raise ModelInputError("DESIGN-1 only evaluates single_round_port")
    if normalized["model"].get("near_field", {}).get("enabled") is not True:
        raise ModelInputError("near_field must be enabled for DESIGN-1")
    if normalized["model"].get("far_field", {}).get("enabled") is True:
        raise ModelInputError("DESIGN-1 cannot evaluate an unimplemented far field")
    for resolution in (section_resolution, plan_resolution):
        if len(resolution) != 2 or any(type(n) is not int or not 15 <= n <= 350 for n in resolution):
            raise ModelInputError("field resolution must be two integers between 15 and 350")
    source = normalized["forcing"]["source"]
    if (("delta_T_C" in source) == ("discharge_temperature_C" in source)
            or "flow_m3h" not in source):
        raise ModelInputError("requires flow_m3h and one source temperature definition")
    thermo = thermodynamics or GswThermodynamics()
    site = normalized["site"]
    latitude, longitude = site["latitude_deg"], site["longitude_deg"]
    depth = normalized["outfall"]["discharge_depth_below_surface_m"]
    depth_levels = sorted({d for d, _ in snapshot.temperature_profile_C} |
                          {d for d, _ in snapshot.salinity_profile_psu})
    td, tv = zip(*snapshot.temperature_profile_C)
    sd, sv = zip(*snapshot.salinity_profile_psu)
    east, north = snapshot.current_east_north_mps
    levels = []
    for d in depth_levels:
        state = thermo.from_practical_salinity_in_situ(
            practical_salinity=float(np.interp(d, sd, sv)),
            in_situ_temperature_C=float(np.interp(d, td, tv)),
            depth_m=d, latitude_deg=latitude, longitude_deg=longitude)
        levels.append(AmbientLevel(d, state, east, north))
    ambient = AmbientColumn.from_levels(levels)
    outlet_temp = float(np.interp(depth, td, tv))
    discharge = (_candidate_scalar("discharge_temperature_C", normalized, snapshot)
                 if "discharge_temperature_C" in source else
                 outlet_temp + _candidate_scalar("delta_T_C", normalized, snapshot))
    if discharge <= outlet_temp:
        raise ModelInputError("DESIGN-1 warm-only plots require discharge temperature above local ambient at outlet")
    salinity = (_candidate_scalar("salinity_psu", normalized, snapshot)
                if "salinity_psu" in source else float(np.interp(depth, sd, sv)))
    flow = _candidate_scalar("flow_m3h", normalized, snapshot)
    if flow <= 0 or salinity < 0:
        raise ModelInputError("flow_m3h must be positive and Practical Salinity non-negative")
    state = thermo.from_practical_salinity_in_situ(
        practical_salinity=salinity, in_situ_temperature_C=discharge,
        depth_m=depth, latitude_deg=latitude, longitude_deg=longitude)
    problem = NearFieldProblem(
        latitude_deg=latitude, longitude_deg=longitude,
        water_depth_m=site["water_depth_m"],
        port=build_near_field_port(normalized["outfall"]),
        source=SourceState(flow_m3s=flow / 3600.0, seawater=state),
        ambient=ambient,
    )
    near = normalized["model"]["near_field"]
    kwargs = near.get("options", {})
    if not isinstance(kwargs, dict) or set(kwargs) - set(NearFieldOptions.__dataclass_fields__):
        raise ModelInputError("unrecognized near_field.options; only NearFieldOptions fields supported")
    try:
        options = NearFieldOptions(**kwargs)
    except (TypeError, ValueError) as exc:
        raise ModelInputError("invalid near_field.options") from exc
    solution = solve_near_field(problem, thermodynamics=thermo, options=options)
    trajectory = solution.sample(np.linspace(0, solution.end_time_s, 90))
    x, y = trajectory.x_east_m, trajectory.y_north_m
    total = math.hypot(float(x[-1]), float(y[-1]))
    heading = (math.degrees(math.atan2(float(x[-1]), float(y[-1]))) % 360.0
               if total > 1e-8 else problem.port.azimuth_deg)
    az = math.radians(heading)
    along = x * math.sin(az) + y * math.cos(az)
    margin = max(0.7, float(max(trajectory.diameter_m)) * 1.3)
    section_dist = np.linspace(min(0.0, float(np.min(along))) - margin,
                               max(0.0, float(np.max(along))) + margin,
                               section_resolution[0])
    section_depth = np.linspace(0.0, site["water_depth_m"], section_resolution[1])
    section = vertical_section(solution, distances_m=section_dist,
                               depths_m=section_depth, heading_deg=heading, samples=90)
    plan_depth = float(np.median(trajectory.depth_m))
    plan = horizontal_plan(solution,
                           east_m=np.linspace(min(0.0, float(np.min(x))) - margin,
                                              max(0.0, float(np.max(x))) + margin,
                                              plan_resolution[0]),
                           north_m=np.linspace(min(0.0, float(np.min(y))) - margin,
                                               max(0.0, float(np.max(y))) + margin,
                                               plan_resolution[1]),
                           depth_m=plan_depth, samples=90)
    threshold = _threshold(normalized)
    sampled = sampled_isotherm_indicators(section, plan, threshold_delta_T_C=threshold)
    metrics = {
        **sampled,
        "section_peak_delta_T_C": float(np.max(section.values.delta_temperature_C)),
        "plan_peak_delta_T_C": float(np.max(plan.values.delta_temperature_C)),
        "plan_slice_depth_m": plan_depth,
        "section_heading_deg": heading,
        "source_ambient_temperature_C": outlet_temp,
        "source_discharge_temperature_C": discharge,
        "source_temperature_excess_C": discharge - outlet_temp,
        "source_salinity_assumption": ("configured source Practical Salinity" if "salinity_psu" in source
                                       else "source SP assumed equal ambient SP at discharge depth"),
        "final_bulk_dilution": float(trajectory.dilution[-1]),
        "termination_reason": str(solution.reason),
        "end_time_s": solution.end_time_s,
        "criterion_status": "NOT_ASSESSED: spatial slice indicators are not a 3-D/receptor permit test",
        "model_status": "UNVALIDATED: MODEL-CLOSURE-1 and FIELD-PROFILE-1 open",
    }
    digest = hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":"),
                                       allow_nan=False, ensure_ascii=False).encode()).hexdigest()
    return DesignEvaluation(normalized, digest, snapshot, solution, section, plan, metrics)
