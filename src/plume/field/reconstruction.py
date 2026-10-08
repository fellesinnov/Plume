"""FIELD-1: headless, reference-profile reconstruction of near-field thermal excess.

The near-field trajectory transports *bulk* Absolute Salinity/Conservative
Temperature. A bounded 3/2-power cross-plume profile reconstructs a field;
its peak/mean relation is an approximation, not physical qualification.
No near-field value is extrapolated past the modeled trajectory end.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import math

import numpy as np
from numpy.typing import NDArray

from ..errors import ModelInputError, ModelError
from ..model.nearfield import AmbientColumn, NearFieldSolution, Trajectory
from ..model.thermodynamics import SeawaterState, Thermodynamics

# PLUMES2.0 (EPA/600/B-24/339), sec. 3.3.1: phi=(1-(r/b)^1.5)^2.
# Area average 2*integral_0^1 phi(q)*q dq = 9/35 for round sections.
PROFILE_ID = "plumes20_three_half_power_bounded_v1"
PEAK_TO_MEAN_LIMIT = 35.0 / 9.0
PROFILE_QUALIFICATION = "reference-formulated; physical/near-source qualification open"


@dataclass(frozen=True, slots=True)
class FieldValues:
    """A gridded near-field prediction in ENU/depth-positive-down conventions.

    `modeled` is true only inside the reconstructed near-field support.
    Zeros outside it mean *no near-field prediction there*, not a far-field
    zero-temperature finding. Every gridded temperature is in-situ excess
    relative to the ambient at the *grid point's depth*.
    """

    east_m: NDArray[np.float64]
    north_m: NDArray[np.float64]
    depth_m: NDArray[np.float64]
    ambient_temperature_C: NDArray[np.float64]
    delta_conservative_temperature_C: NDArray[np.float64]
    delta_absolute_salinity_gkg: NDArray[np.float64]
    delta_temperature_C: NDArray[np.float64]
    modeled: NDArray[np.bool_]
    profile_id: str = PROFILE_ID
    qualification: str = PROFILE_QUALIFICATION


@dataclass(frozen=True, slots=True)
class FieldSlice:
    """Section (distance, depth) or physical plan (east, north at one depth)."""

    values: FieldValues
    plane: Literal["section", "plan"]
    horizontal_axis_m: NDArray[np.float64]
    vertical_axis_m: NDArray[np.float64]
    heading_or_depth: float


def radial_weight(normalized_radius: NDArray[np.float64] | float,
                  dilution: NDArray[np.float64] | float) -> NDArray[np.float64]:
    """Normalized 3/2 profile whose area-average is exactly one.

    Fully developed peak/mean is 35/9 for a top-hat cross-section velocity.
    At finite source dilution D, the peak is capped to min(D, 35/9) by
    convexly blending top-hat and 3/2 profiles; this avoids predicting more
    than 100% source tracer at the outlet without selecting an empirical
    development length. The blend is a protective assumption, not calibrated
    evidence. Profile support ends at r/b=1.
    """

    q, d = np.broadcast_arrays(np.asarray(normalized_radius, dtype=float),
                               np.asarray(dilution, dtype=float))
    if not (np.all(np.isfinite(q)) and np.all(np.isfinite(d))):
        raise ModelInputError("radial coordinate and dilution must be finite")
    if np.any(q < 0.0) or np.any(d < 1.0):
        raise ModelInputError("normalized radius must be >= 0 and dilution >= 1")
    blend = np.clip((d - 1.0) / (PEAK_TO_MEAN_LIMIT - 1.0), 0.0, 1.0)
    shape = np.square(1.0 - np.power(np.minimum(q, 1.0), 1.5))
    return np.where(q <= 1.0, 1.0 - blend + blend * PEAK_TO_MEAN_LIMIT * shape, 0.0)


def _trajectory_inputs(trajectory: Trajectory, ambient: AmbientColumn,
                       water_depth_m: float) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    center = np.column_stack((trajectory.x_east_m, trajectory.y_north_m, trajectory.z_up_m))
    radius = np.asarray(trajectory.diameter_m, dtype=float) / 2.0
    dilution = np.asarray(trajectory.dilution, dtype=float)
    n = len(trajectory)
    scalar_arrays = (radius, dilution, trajectory.depth_m, trajectory.time_s,
                     trajectory.conservative_temperature_C,
                     trajectory.absolute_salinity_gkg)
    if (n < 2 or center.shape != (n, 3) or
            any(np.asarray(v).shape != (n,) for v in scalar_arrays) or
            not np.all(np.isfinite(center)) or
            any(not np.all(np.isfinite(v)) for v in scalar_arrays)):
        raise ModelInputError("trajectory requires >=2 finite aligned state samples")
    if np.any(radius <= 0.0) or np.any(dilution < 1.0 - 1e-9):
        raise ModelInputError("trajectory radius must be positive and dilution >= 1")
    if np.any(np.diff(trajectory.time_s) <= 0.0):
        raise ModelInputError("trajectory times must increase strictly")
    if np.any(np.linalg.norm(np.diff(center, axis=0), axis=1) <= 1e-12):
        raise ModelInputError("trajectory has a zero-length centerline segment")
    if (np.any(trajectory.depth_m < -1e-8) or
            np.any(trajectory.depth_m > water_depth_m + 1e-8) or
            not np.allclose(trajectory.depth_m, -center[:, 2], atol=1e-8, rtol=0)):
        raise ModelInputError("trajectory depth and ENU z must agree in the water column")
    levels = ambient.levels
    depth = [level.depth_m for level in levels]
    ambient_ct = np.interp(trajectory.depth_m, depth,
                           [level.seawater.conservative_temperature_C for level in levels])
    ambient_sa = np.interp(trajectory.depth_m, depth,
                           [level.seawater.absolute_salinity_gkg for level in levels])
    return center, radius, np.column_stack((
        np.asarray(trajectory.conservative_temperature_C) - ambient_ct,
        np.asarray(trajectory.absolute_salinity_gkg) - ambient_sa,
        dilution,
    ))


def reconstruct_points(
    trajectory: Trajectory, *, ambient: AmbientColumn,
    thermodynamics: Thermodynamics, latitude_deg: float, water_depth_m: float,
    east_m: NDArray[np.float64] | float,
    north_m: NDArray[np.float64] | float,
    depth_m: NDArray[np.float64] | float,
    chunk_size: int = 4096,
) -> FieldValues:
    """Reconstruct one near-field 3-D sample grid from MODEL-1 trajectory.

    Nearest finite polyline segment in *three dimensions* supplies radius,
    dilution and bulk scalar anomalies. This is a curved-tube approximation;
    at self-overlap the nearest branch wins, without summing fluid twice.
    Axial end caps prevent fictional downstream continuation. Site stratification
    supplies each grid cell's local reference ambient, and the injected TEOS
    boundary converts locally perturbed SA/CT to in-situ temperature.
    """

    if (not math.isfinite(latitude_deg) or not -90.0 <= latitude_deg <= 90.0 or
            not math.isfinite(water_depth_m) or water_depth_m <= 0):
        raise ModelInputError("valid latitude and positive water depth required")
    if not isinstance(chunk_size, int) or chunk_size < 1:
        raise ModelInputError("chunk_size must be a positive integer")
    try:
        x, y, depth = np.broadcast_arrays(
            np.asarray(east_m, dtype=float), np.asarray(north_m, dtype=float),
            np.asarray(depth_m, dtype=float))
    except ValueError as exc:
        raise ModelInputError("grid east/north/depth must broadcast") from exc
    if (not all(np.all(np.isfinite(v)) for v in (x, y, depth)) or
            np.any(depth < 0) or np.any(depth > water_depth_m)):
        raise ModelInputError("field grid must be finite and inside the water column")
    center, radius, scalars = _trajectory_inputs(trajectory, ambient, water_depth_m)
    starts, offsets = center[:-1], np.diff(center, axis=0)
    length_squared = np.einsum("ij,ij->i", offsets, offsets)
    n_segments = len(offsets)
    xyz = np.column_stack((x.ravel(), y.ravel(), -depth.ravel()))
    delta_ct = np.zeros(xyz.shape[0], dtype=float)
    delta_sa = np.zeros(xyz.shape[0], dtype=float)
    supported = np.zeros(xyz.shape[0], dtype=bool)

    for start_idx in range(0, len(xyz), chunk_size):
        end_idx = min(start_idx + chunk_size, len(xyz))
        pts = xyz[start_idx:end_idx]
        relative = pts[:, None, :] - starts[None, :, :]
        raw_fraction = np.einsum("kij,ij->ki", relative, offsets) / length_squared
        fraction = np.clip(raw_fraction, 0.0, 1.0)
        perpendicular = relative - fraction[:, :, None] * offsets[None, :, :]
        distance_squared = np.einsum("kij,kij->ki", perpendicular, perpendicular)
        closest = np.argmin(distance_squared, axis=1)
        ix = np.arange(len(pts))
        t = fraction[ix, closest]
        raw_t = raw_fraction[ix, closest]
        r2 = distance_squared[ix, closest]
        b = radius[closest] + t * (radius[closest + 1] - radius[closest])
        axial = ((closest != 0) | (raw_t >= 0.0)) & (
            (closest != n_segments - 1) | (raw_t <= 1.0))
        active = axial & (r2 <= b * b)
        if not np.any(active):
            continue
        dilution = scalars[closest, 2] + t * (scalars[closest + 1, 2] - scalars[closest, 2])
        d_ct = scalars[closest, 0] + t * (scalars[closest + 1, 0] - scalars[closest, 0])
        d_sa = scalars[closest, 1] + t * (scalars[closest + 1, 1] - scalars[closest, 1])
        weight = radial_weight(np.sqrt(r2[active]) / b[active], np.maximum(1.0, dilution[active]))
        indices = start_idx + np.flatnonzero(active)
        delta_ct[indices] = d_ct[active] * weight
        delta_sa[indices] = d_sa[active] * weight
        supported[indices] = True

    levels = ambient.levels
    water_levels = np.array([level.depth_m for level in levels], dtype=float)
    sa_levels = np.array([level.seawater.absolute_salinity_gkg for level in levels])
    ct_levels = np.array([level.seawater.conservative_temperature_C for level in levels])
    local_sa = np.interp(depth.ravel(), water_levels, sa_levels)
    local_ct = np.interp(depth.ravel(), water_levels, ct_levels)
    # Profiles normally share depth rows. Evaluate the baseline only at unique
    # depths rather than executing identical thermodynamic conversions per pixel.
    unique_depths, inverse = np.unique(depth.ravel(), return_inverse=True)
    ambient_t_by_depth = np.empty(len(unique_depths))
    for i, d in enumerate(unique_depths):
        s = SeawaterState(float(np.interp(d, water_levels, sa_levels)),
                          float(np.interp(d, water_levels, ct_levels)))
        ambient_t_by_depth[i] = thermodynamics.in_situ_temperature_C(
            s, depth_m=float(d), latitude_deg=latitude_deg)
    ambient_t = ambient_t_by_depth[inverse]
    excess_t = np.zeros(len(xyz), dtype=float)
    for i in np.flatnonzero(supported):
        salinity = float(local_sa[i] + delta_sa[i])
        if salinity < -1e-9:
            raise ModelError("profile reconstructs negative Absolute Salinity in strong stratification")
        state = SeawaterState(max(salinity, 0.0), float(local_ct[i] + delta_ct[i]))
        temp = thermodynamics.in_situ_temperature_C(
            state, depth_m=float(depth.ravel()[i]), latitude_deg=latitude_deg)
        excess_t[i] = temp - ambient_t[i]
    if not np.all(np.isfinite(excess_t)) or not np.all(np.isfinite(ambient_t)):
        raise ModelError("non-finite TEOS-10 temperature during field reconstruction")
    return FieldValues(
        east_m=x.copy(), north_m=y.copy(), depth_m=depth.copy(),
        ambient_temperature_C=ambient_t.reshape(x.shape),
        delta_conservative_temperature_C=delta_ct.reshape(x.shape),
        delta_absolute_salinity_gkg=delta_sa.reshape(x.shape),
        delta_temperature_C=excess_t.reshape(x.shape),
        modeled=supported.reshape(x.shape),
    )


def _samples(solution: NearFieldSolution, samples: int) -> Trajectory:
    if not isinstance(samples, int) or samples < 2:
        raise ModelInputError("at least two trajectory samples are required")
    return solution.sample(np.linspace(0.0, solution.end_time_s, samples))


def _axis(name: str, data: NDArray[np.float64] | list[float]) -> NDArray[np.float64]:
    axis = np.asarray(data, dtype=float)
    if (axis.ndim != 1 or len(axis) < 2 or not np.all(np.isfinite(axis)) or
            not np.all(np.diff(axis) > 0.0)):
        raise ModelInputError(f"{name} must be finite, increasing, with >=2 values")
    return axis


def vertical_section(
    solution: NearFieldSolution, *, distances_m: NDArray[np.float64] | list[float],
    depths_m: NDArray[np.float64] | list[float],
    heading_deg: float | None = None, samples: int = 300,
) -> FieldSlice:
    """Physical vertical ENU plane through the outlet, not a projected plume."""
    ds, zs = _axis("distances_m", distances_m), _axis("depths_m", depths_m)
    trajectory = _samples(solution, samples)
    if heading_deg is None:
        east, north = float(trajectory.x_east_m[-1]), float(trajectory.y_north_m[-1])
        heading_deg = (math.degrees(math.atan2(east, north)) % 360.0
                       if math.hypot(east, north) > 1e-9 else solution.problem.port.azimuth_deg)
    if not math.isfinite(heading_deg):
        raise ModelInputError("section heading must be finite")
    az = math.radians(heading_deg)
    longitudinal, grid_depth = np.meshgrid(ds, zs)
    values = reconstruct_points(
        trajectory, ambient=solution.problem.ambient,
        thermodynamics=solution.thermodynamics,
        latitude_deg=solution.problem.latitude_deg,
        water_depth_m=solution.problem.water_depth_m,
        east_m=longitudinal * math.sin(az),
        north_m=longitudinal * math.cos(az), depth_m=grid_depth)
    return FieldSlice(values, "section", ds, zs, float(heading_deg % 360.0))


def horizontal_plan(
    solution: NearFieldSolution, *, east_m: NDArray[np.float64] | list[float],
    north_m: NDArray[np.float64] | list[float], depth_m: float, samples: int = 300,
) -> FieldSlice:
    """Physical horizontal slice at ONE positive-down depth (not depth max)."""
    east, north = _axis("east_m", east_m), _axis("north_m", north_m)
    x, y = np.meshgrid(east, north)
    values = reconstruct_points(
        _samples(solution, samples), ambient=solution.problem.ambient,
        thermodynamics=solution.thermodynamics,
        latitude_deg=solution.problem.latitude_deg,
        water_depth_m=solution.problem.water_depth_m,
        east_m=x, north_m=y, depth_m=depth_m)
    return FieldSlice(values, "plan", east, north, float(depth_m))
