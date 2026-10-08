"""MODEL-1 single-round-port Lagrangian near-field kernel.

The conserved-state architecture, source contraction, element stretching, and
continuous-integration structure are adapted from Ebb Carbon's MIT-licensed
``Plumes_Public`` implementation pinned by REF-1.  Plume deliberately changes
three boundaries:

* coordinates are product-native ENU with navigation azimuth;
* the production state transports TEOS-10 Absolute Salinity and Conservative
  Temperature rather than legacy S/T scalars;
* closure choice remains an internal qualification seam while
  MODEL-CLOSURE-1 is open.

Similarity-profile/field reconstruction, plume merging, and far-field transport
are intentionally outside this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from ..errors import ModelError, ModelInputError
from .entrainment import ClosureKind, EntrainmentClosure, closure_from_kind
from .thermodynamics import SeawaterState, Thermodynamics

GRAVITY_M_S2 = 9.80665
_STATE_SIZE = 9
_PATH_DERIVATIVE_ITERATIONS = 6
_PATH_DERIVATIVE_TOLERANCE = 1e-12


def _require_finite(name: str, *values: float) -> None:
    if not all(math.isfinite(float(value)) for value in values):
        raise ModelInputError(f"{name} must be finite")


def _density_kg_m3(
    thermodynamics: Thermodynamics,
    state: SeawaterState,
    *,
    depth_m: float,
    latitude_deg: float,
) -> float:
    density = float(
        thermodynamics.density_kg_m3(
            state,
            depth_m=depth_m,
            latitude_deg=latitude_deg,
        )
    )
    if not math.isfinite(density) or density <= 0.0:
        raise ModelError("thermodynamic density must be finite and > 0")
    return density


@dataclass(frozen=True, slots=True)
class SingleRoundPort:
    diameter_m: float
    discharge_depth_below_surface_m: float
    vertical_angle_deg: float
    azimuth_deg: float

    def __post_init__(self) -> None:
        _require_finite(
            "single-round-port geometry",
            self.diameter_m,
            self.discharge_depth_below_surface_m,
            self.vertical_angle_deg,
            self.azimuth_deg,
        )
        if self.diameter_m <= 0.0:
            raise ModelInputError("port diameter_m must be > 0")
        if self.discharge_depth_below_surface_m < 0.0:
            raise ModelInputError("port discharge depth must be >= 0")
        if not -90.0 <= self.vertical_angle_deg <= 90.0:
            raise ModelInputError("vertical_angle_deg must be between -90 and 90")
        if not 0.0 <= self.azimuth_deg < 360.0:
            raise ModelInputError("azimuth_deg must be in [0, 360)")

    def velocity_vector(self, speed_mps: float) -> NDArray[np.float64]:
        """ENU velocity; azimuth is clockwise from true north."""

        vertical = math.radians(self.vertical_angle_deg)
        azimuth = math.radians(self.azimuth_deg)
        horizontal = speed_mps * math.cos(vertical)
        return np.array(
            [
                horizontal * math.sin(azimuth),
                horizontal * math.cos(azimuth),
                speed_mps * math.sin(vertical),
            ],
            dtype=np.float64,
        )


@dataclass(frozen=True, slots=True)
class SourceState:
    flow_m3s: float
    seawater: SeawaterState

    def __post_init__(self) -> None:
        _require_finite("source flow_m3s", self.flow_m3s)
        if self.flow_m3s <= 0.0:
            raise ModelInputError("source flow_m3s must be > 0")


@dataclass(frozen=True, slots=True)
class AmbientLevel:
    depth_m: float
    seawater: SeawaterState
    u_east_mps: float = 0.0
    v_north_mps: float = 0.0

    def __post_init__(self) -> None:
        _require_finite(
            "ambient level", self.depth_m, self.u_east_mps, self.v_north_mps
        )
        if self.depth_m < 0.0:
            raise ModelInputError("ambient depth_m must be >= 0")


@dataclass(frozen=True, slots=True)
class AmbientSample:
    depth_m: float
    seawater: SeawaterState
    density_kg_m3: float
    velocity_mps: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class AmbientColumn:
    """Normalized depth profile; thermodynamics is injected by the solver."""

    levels: tuple[AmbientLevel, ...]

    def __post_init__(self) -> None:
        if len(self.levels) < 2:
            raise ModelInputError("ambient column requires at least two depth levels")
        depths = [level.depth_m for level in self.levels]
        if any(b <= a for a, b in zip(depths, depths[1:], strict=False)):
            raise ModelInputError("ambient depths must be strictly increasing")

    @classmethod
    def from_levels(cls, levels: Iterable[AmbientLevel]) -> "AmbientColumn":
        return cls(tuple(levels))

    @property
    def maximum_depth_m(self) -> float:
        return self.levels[-1].depth_m

    def require_full_water_column(self, water_depth_m: float) -> None:
        depths = [level.depth_m for level in self.levels]
        if abs(depths[0]) > 1e-9 or abs(depths[-1] - water_depth_m) > 1e-9:
            raise ModelInputError(
                "ambient profile must explicitly cover the full water column from 0 to water_depth_m"
            )

    def sample(
        self,
        depth_m: float,
        *,
        water_depth_m: float,
        latitude_deg: float,
        thermodynamics: Thermodynamics,
    ) -> AmbientSample:
        # The solver's root finder can evaluate a trial just beyond a boundary.
        # Because the profile explicitly covers both physical boundaries, clamping
        # here is only numerical boundary handling, not provider extrapolation.
        depth = min(max(float(depth_m), 0.0), water_depth_m)
        depths = np.array([level.depth_m for level in self.levels], dtype=np.float64)
        absolute = np.array(
            [level.seawater.absolute_salinity_gkg for level in self.levels],
            dtype=np.float64,
        )
        conservative = np.array(
            [level.seawater.conservative_temperature_C for level in self.levels],
            dtype=np.float64,
        )
        u = np.array([level.u_east_mps for level in self.levels], dtype=np.float64)
        v = np.array([level.v_north_mps for level in self.levels], dtype=np.float64)
        seawater = SeawaterState(
            absolute_salinity_gkg=float(np.interp(depth, depths, absolute)),
            conservative_temperature_C=float(np.interp(depth, depths, conservative)),
        )
        density = _density_kg_m3(
            thermodynamics,
            seawater,
            depth_m=depth,
            latitude_deg=latitude_deg,
        )
        return AmbientSample(
            depth_m=depth,
            seawater=seawater,
            density_kg_m3=density,
            velocity_mps=np.array(
                [
                    float(np.interp(depth, depths, u)),
                    float(np.interp(depth, depths, v)),
                    0.0,
                ],
                dtype=np.float64,
            ),
        )


@dataclass(frozen=True, slots=True)
class NearFieldProblem:
    latitude_deg: float
    longitude_deg: float
    water_depth_m: float
    port: SingleRoundPort
    source: SourceState
    ambient: AmbientColumn

    def __post_init__(self) -> None:
        _require_finite(
            "near-field site", self.latitude_deg, self.longitude_deg, self.water_depth_m
        )
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ModelInputError("latitude_deg must be between -90 and 90")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ModelInputError("longitude_deg must be between -180 and 180")
        if self.water_depth_m <= 0.0:
            raise ModelInputError("water_depth_m must be > 0")
        self.ambient.require_full_water_column(self.water_depth_m)
        if self.port.discharge_depth_below_surface_m > self.water_depth_m:
            raise ModelInputError("port discharge depth cannot exceed water depth")


class TerminationReason(StrEnum):
    OSCILLATION_LIMIT = "oscillation_limit"
    SURFACE = "surface"
    SEABED = "seabed"
    DILUTION_LIMIT = "dilution_limit"
    TIME_LIMIT = "time_limit"
    NON_PHYSICAL = "non_physical"


class OscillationKind(StrEnum):
    TRAP = "trap"
    REVERSAL = "reversal"


@dataclass(frozen=True, slots=True, order=True)
class OscillationEvent:
    time_s: float
    kind: OscillationKind


@dataclass(frozen=True, slots=True)
class NearFieldOptions:
    contraction_coefficient: float = 0.61
    aspiration_coefficient: float = 0.10
    closure: ClosureKind = ClosureKind.UM3_REFERENCE
    max_time_s: float = 3600.0
    max_dilution: float = 10000.0
    oscillation_event_limit: int = 4
    stop_at_surface: bool = True
    stop_at_seabed: bool = True
    rtol: float = 1e-6
    atol: float = 1e-9

    def __post_init__(self) -> None:
        _require_finite(
            "near-field options",
            self.contraction_coefficient,
            self.aspiration_coefficient,
            self.max_time_s,
            self.max_dilution,
            self.rtol,
            self.atol,
        )
        if not 0.0 < self.contraction_coefficient <= 1.0:
            raise ModelInputError("contraction_coefficient must be in (0, 1]")
        if self.aspiration_coefficient < 0.0:
            raise ModelInputError("aspiration_coefficient must be >= 0")
        if self.max_time_s <= 0.0:
            raise ModelInputError("max_time_s must be > 0")
        if self.max_dilution <= 1.0:
            raise ModelInputError("max_dilution must be > 1")
        if self.oscillation_event_limit < 1:
            raise ModelInputError("oscillation_event_limit must be >= 1")
        if self.rtol <= 0.0 or self.atol <= 0.0:
            raise ModelInputError("solver tolerances must be > 0")


@dataclass(frozen=True, slots=True)
class _Geometry:
    radius_constant: float
    effluent_mass_kg: float

    def radius_m(self, mass_kg: float, density_kg_m3: float, speed_mps: float) -> float:
        if mass_kg <= 0.0 or density_kg_m3 <= 0.0 or speed_mps <= 0.0:
            raise ModelError("near-field geometry requires positive mass, density, and speed")
        return math.sqrt(
            self.radius_constant * mass_kg / (density_kg_m3 * speed_mps)
        )

    def dilution(self, mass_kg: NDArray[np.float64] | float) -> NDArray[np.float64]:
        return np.asarray(mass_kg, dtype=np.float64) / self.effluent_mass_kg


@dataclass(frozen=True, slots=True)
class _State:
    mass_kg: float
    velocity_mps: NDArray[np.float64]
    seawater: SeawaterState
    position_enu_m: NDArray[np.float64]

    @property
    def speed_mps(self) -> float:
        return float(np.linalg.norm(self.velocity_mps))

    @property
    def depth_m(self) -> float:
        return -float(self.position_enu_m[2])

    def pack(self) -> NDArray[np.float64]:
        return np.concatenate(
            (
                [self.mass_kg],
                self.mass_kg * self.velocity_mps,
                [
                    self.mass_kg * self.seawater.conservative_temperature_C,
                    self.mass_kg * self.seawater.absolute_salinity_gkg,
                ],
                self.position_enu_m,
            )
        )


def _unpack(vector: NDArray[np.float64]) -> _State:
    if vector.shape[-1] != _STATE_SIZE:
        raise ModelError(f"expected state vector length {_STATE_SIZE}, got {vector.shape}")
    mass = float(vector[0])
    if mass <= 0.0:
        raise ModelError("near-field element mass must remain positive")
    return _State(
        mass_kg=mass,
        velocity_mps=np.asarray(vector[1:4], dtype=np.float64) / mass,
        seawater=SeawaterState(
            absolute_salinity_gkg=float(vector[5]) / mass,
            conservative_temperature_C=float(vector[4]) / mass,
        ),
        position_enu_m=np.asarray(vector[6:9], dtype=np.float64),
    )


@dataclass(frozen=True, slots=True)
class Trajectory:
    time_s: NDArray[np.float64]
    dilution: NDArray[np.float64]
    diameter_m: NDArray[np.float64]
    x_east_m: NDArray[np.float64]
    y_north_m: NDArray[np.float64]
    z_up_m: NDArray[np.float64]
    depth_m: NDArray[np.float64]
    speed_mps: NDArray[np.float64]
    absolute_salinity_gkg: NDArray[np.float64]
    conservative_temperature_C: NDArray[np.float64]
    in_situ_temperature_C: NDArray[np.float64]
    ambient_in_situ_temperature_C: NDArray[np.float64]
    excess_temperature_C: NDArray[np.float64]
    plume_density_kg_m3: NDArray[np.float64]

    def __len__(self) -> int:
        return int(self.time_s.size)


@dataclass(frozen=True, slots=True)
class NearFieldSolution:
    problem: NearFieldProblem
    options: NearFieldOptions
    reason: TerminationReason
    end_time_s: float
    events: dict[str, float]
    oscillations: tuple[OscillationEvent, ...]
    geometry: _Geometry = field(repr=False)
    thermodynamics: Thermodynamics = field(repr=False, compare=False)
    raw_solution: object = field(repr=False, compare=False)

    def sample(self, times_s: NDArray[np.float64] | list[float]) -> Trajectory:
        requested = np.asarray(times_s, dtype=np.float64)
        if requested.ndim != 1:
            raise ModelInputError("sample times must be one-dimensional")
        if requested.size and (
            float(requested.min()) < -1e-12
            or float(requested.max()) > self.end_time_s + 1e-9
        ):
            raise ModelInputError("sample times must lie within the near-field interval")
        raw = self.raw_solution.sol(requested)  # type: ignore[attr-defined]
        mass = raw[0]
        velocity = raw[1:4] / mass
        speed = np.linalg.norm(velocity, axis=0)
        conservative = raw[4] / mass
        absolute = raw[5] / mass
        depth = -raw[8]
        plume_density = np.empty_like(mass)
        in_situ = np.empty_like(mass)
        ambient_temp = np.empty_like(mass)
        radius = np.empty_like(mass)
        for index in range(mass.size):
            state = SeawaterState(float(absolute[index]), float(conservative[index]))
            d = float(depth[index])
            plume_density[index] = _density_kg_m3(
                self.thermodynamics,
                state,
                depth_m=d,
                latitude_deg=self.problem.latitude_deg,
            )
            in_situ[index] = self.thermodynamics.in_situ_temperature_C(
                state,
                depth_m=d,
                latitude_deg=self.problem.latitude_deg,
            )
            ambient = self.problem.ambient.sample(
                d,
                water_depth_m=self.problem.water_depth_m,
                latitude_deg=self.problem.latitude_deg,
                thermodynamics=self.thermodynamics,
            )
            ambient_temp[index] = self.thermodynamics.in_situ_temperature_C(
                ambient.seawater,
                depth_m=ambient.depth_m,
                latitude_deg=self.problem.latitude_deg,
            )
            radius[index] = self.geometry.radius_m(
                float(mass[index]),
                float(plume_density[index]),
                float(speed[index]),
            )
        return Trajectory(
            time_s=requested,
            dilution=self.geometry.dilution(mass),
            diameter_m=2.0 * radius,
            x_east_m=raw[6],
            y_north_m=raw[7],
            z_up_m=raw[8],
            depth_m=depth,
            speed_mps=speed,
            absolute_salinity_gkg=absolute,
            conservative_temperature_C=conservative,
            in_situ_temperature_C=in_situ,
            ambient_in_situ_temperature_C=ambient_temp,
            excess_temperature_C=in_situ - ambient_temp,
            plume_density_kg_m3=plume_density,
        )


def _initial_state(
    problem: NearFieldProblem,
    thermodynamics: Thermodynamics,
    options: NearFieldOptions,
) -> tuple[_State, _Geometry]:
    radius = 0.5 * problem.port.diameter_m * math.sqrt(options.contraction_coefficient)
    contracted_area = math.pi * radius * radius
    speed = problem.source.flow_m3s / contracted_area
    depth = problem.port.discharge_depth_below_surface_m
    density = _density_kg_m3(
        thermodynamics,
        problem.source.seawater,
        depth_m=depth,
        latitude_deg=problem.latitude_deg,
    )
    thickness = radius
    mass = density * math.pi * radius * radius * thickness
    if depth - radius <= 0.0:
        raise ModelInputError("contracted source element intersects the free surface")
    if depth + radius >= problem.water_depth_m:
        raise ModelInputError("contracted source element intersects the seabed")
    state = _State(
        mass_kg=mass,
        velocity_mps=problem.port.velocity_vector(speed),
        seawater=problem.source.seawater,
        position_enu_m=np.array([0.0, 0.0, -depth], dtype=np.float64),
    )
    geometry = _Geometry(
        radius_constant=radius * radius * density * speed / mass,
        effluent_mass_kg=mass,
    )
    return state, geometry


def _density_rate(
    *,
    state: _State,
    salinity_rate: float,
    temperature_rate: float,
    depth_rate: float,
    thermodynamics: Thermodynamics,
    latitude_deg: float,
    water_depth_m: float,
) -> float:
    """Total material density derivative, including TEOS-10 pressure change."""

    salinity_step = 1e-4
    temperature_step = 1e-4
    depth_step = 1e-3
    sa = state.seawater.absolute_salinity_gkg
    ct = state.seawater.conservative_temperature_C
    depth = min(max(state.depth_m, 0.0), water_depth_m)

    low_sa = max(0.0, sa - salinity_step)
    high_sa = sa + salinity_step

    def rho(sa_value: float, ct_value: float, depth_value: float) -> float:
        return _density_kg_m3(
            thermodynamics,
            SeawaterState(sa_value, ct_value),
            depth_m=min(max(depth_value, 0.0), water_depth_m),
            latitude_deg=latitude_deg,
        )

    drho_dsa = (rho(high_sa, ct, depth) - rho(low_sa, ct, depth)) / (high_sa - low_sa)
    drho_dct = (
        rho(sa, ct + temperature_step, depth)
        - rho(sa, ct - temperature_step, depth)
    ) / (2.0 * temperature_step)
    low_depth = max(0.0, depth - depth_step)
    high_depth = min(water_depth_m, depth + depth_step)
    if high_depth == low_depth:
        drho_ddepth = 0.0
    else:
        drho_ddepth = (
            rho(sa, ct, high_depth) - rho(sa, ct, low_depth)
        ) / (high_depth - low_depth)
    return (
        drho_dsa * salinity_rate
        + drho_dct * temperature_rate
        + drho_ddepth * depth_rate
    )


def _make_rhs(
    *,
    problem: NearFieldProblem,
    geometry: _Geometry,
    thermodynamics: Thermodynamics,
    options: NearFieldOptions,
    closure: EntrainmentClosure,
):
    alpha = options.aspiration_coefficient

    def rhs(_time_s: float, vector: NDArray[np.float64]) -> NDArray[np.float64]:
        state = _unpack(vector)
        ambient = problem.ambient.sample(
            state.depth_m,
            water_depth_m=problem.water_depth_m,
            latitude_deg=problem.latitude_deg,
            thermodynamics=thermodynamics,
        )
        plume_density = _density_kg_m3(
            thermodynamics,
            state.seawater,
            depth_m=min(max(state.depth_m, 0.0), problem.water_depth_m),
            latitude_deg=problem.latitude_deg,
        )
        speed = state.speed_mps
        radius = geometry.radius_m(state.mass_kg, plume_density, speed)
        thickness = state.mass_kg / (plume_density * math.pi * radius * radius)
        buoyancy = np.array(
            [
                0.0,
                0.0,
                state.mass_kg
                * (ambient.density_kg_m3 - plume_density)
                / plume_density
                * GRAVITY_M_S2,
            ],
            dtype=np.float64,
        )

        def closure_rate(radius_gradient: float, elevation_gradient: float) -> float:
            return closure.rate_kg_s(
                ambient_density_kg_m3=ambient.density_kg_m3,
                ambient_velocity_mps=ambient.velocity_mps,
                plume_velocity_mps=state.velocity_mps,
                radius_m=radius,
                thickness_m=thickness,
                radius_gradient=radius_gradient,
                elevation_gradient=elevation_gradient,
                aspiration_coefficient=alpha,
            )

        entrainment = closure_rate(0.0, 0.0)
        horizontal = float(np.hypot(state.velocity_mps[0], state.velocity_mps[1]))
        for _ in range(_PATH_DERIVATIVE_ITERATIONS):
            acceleration = (
                (ambient.velocity_mps - state.velocity_mps) * entrainment + buoyancy
            ) / state.mass_kg
            speed_rate = float(np.dot(state.velocity_mps, acceleration)) / speed
            salinity_rate = (
                ambient.seawater.absolute_salinity_gkg
                - state.seawater.absolute_salinity_gkg
            ) * entrainment / state.mass_kg
            temperature_rate = (
                ambient.seawater.conservative_temperature_C
                - state.seawater.conservative_temperature_C
            ) * entrainment / state.mass_kg
            depth_rate = -float(state.velocity_mps[2])
            density_rate = _density_rate(
                state=state,
                salinity_rate=salinity_rate,
                temperature_rate=temperature_rate,
                depth_rate=depth_rate,
                thermodynamics=thermodynamics,
                latitude_deg=problem.latitude_deg,
                water_depth_m=problem.water_depth_m,
            )
            radius_rate = 0.5 * radius * (
                entrainment / state.mass_kg
                - density_rate / plume_density
                - speed_rate / speed
            )
            if horizontal > 1e-12:
                horizontal_rate = (
                    state.velocity_mps[0] * acceleration[0]
                    + state.velocity_mps[1] * acceleration[1]
                ) / horizontal
            else:
                # At an exactly vertical trajectory h = hypot(u, v) is
                # non-differentiable in direction, but its one-sided growth
                # rate under cross-current acceleration is |a_horizontal|.
                # Keeping that limit matters for vertical-jet qualification:
                # otherwise the first bending/curvature derivative is
                # incorrectly forced to zero.
                horizontal_rate = float(np.linalg.norm(acceleration[:2]))
            elevation_rate = (
                horizontal * acceleration[2]
                - state.velocity_mps[2] * horizontal_rate
            ) / (speed * speed)
            updated = closure_rate(radius_rate / speed, elevation_rate / speed)
            if abs(updated - entrainment) <= _PATH_DERIVATIVE_TOLERANCE * max(updated, 1e-30):
                entrainment = updated
                break
            entrainment = updated

        derivative = np.empty_like(vector)
        derivative[0] = entrainment
        derivative[1:4] = ambient.velocity_mps * entrainment + buoyancy
        derivative[4] = ambient.seawater.conservative_temperature_C * entrainment
        derivative[5] = ambient.seawater.absolute_salinity_gkg * entrainment
        derivative[6:9] = state.velocity_mps
        return derivative

    return rhs


def solve_near_field(
    problem: NearFieldProblem,
    *,
    thermodynamics: Thermodynamics,
    options: NearFieldOptions | None = None,
) -> NearFieldSolution:
    """Solve one quasi-steady single-port near-field state.

    ``UM3_REFERENCE`` is the current qualification/software-regression default,
    not a frozen customer-facing production closure.  MODEL-CLOSURE-1 remains
    open until independent Fan calibration/formulation evidence is followed by
    untouched Lee-Cheung hold-back evaluation.
    """

    options = options or NearFieldOptions()
    state0, geometry = _initial_state(problem, thermodynamics, options)
    closure = closure_from_kind(options.closure)
    rhs = _make_rhs(
        problem=problem,
        geometry=geometry,
        thermodynamics=thermodynamics,
        options=options,
        closure=closure,
    )

    def current_radius(vector: NDArray[np.float64]) -> tuple[_State, float]:
        state = _unpack(vector)
        density = _density_kg_m3(
            thermodynamics,
            state.seawater,
            depth_m=min(max(state.depth_m, 0.0), problem.water_depth_m),
            latitude_deg=problem.latitude_deg,
        )
        return state, geometry.radius_m(state.mass_kg, density, state.speed_mps)

    def surface(_t: float, vector: NDArray[np.float64]) -> float:
        state, radius = current_radius(vector)
        return state.depth_m - radius

    def seabed(_t: float, vector: NDArray[np.float64]) -> float:
        state, radius = current_radius(vector)
        return problem.water_depth_m - (state.depth_m + radius)

    def dilution_limit(_t: float, vector: NDArray[np.float64]) -> float:
        return float(geometry.dilution(float(vector[0]))) - options.max_dilution

    def trapping(_t: float, vector: NDArray[np.float64]) -> float:
        state = _unpack(vector)
        depth = min(max(state.depth_m, 0.0), problem.water_depth_m)
        plume_density = _density_kg_m3(
            thermodynamics,
            state.seawater,
            depth_m=depth,
            latitude_deg=problem.latitude_deg,
        )
        return plume_density - problem.ambient.sample(
            depth,
            water_depth_m=problem.water_depth_m,
            latitude_deg=problem.latitude_deg,
            thermodynamics=thermodynamics,
        ).density_kg_m3

    def reversal(_t: float, vector: NDArray[np.float64]) -> float:
        return float(vector[3] / vector[0])

    def nonphysical(_t: float, vector: NDArray[np.float64]) -> float:
        # Mass cannot decrease under a non-negative entrainment closure, and
        # zero salinity is a valid freshwater limit.  The practical numerical
        # singularity is a motionless element, because radius and path
        # derivatives contain 1/|V|.
        if vector[0] <= 0.0:
            return -1.0
        speed = float(np.linalg.norm(vector[1:4] / vector[0]))
        return speed - 1e-10

    for event in (surface, seabed, dilution_limit, nonphysical):
        event.terminal = True  # type: ignore[attr-defined]
        event.direction = -1.0  # type: ignore[attr-defined]
    dilution_limit.direction = 1.0  # type: ignore[attr-defined]
    surface.terminal = options.stop_at_surface  # type: ignore[attr-defined]
    seabed.terminal = options.stop_at_seabed  # type: ignore[attr-defined]
    for event in (trapping, reversal):
        event.terminal = False  # type: ignore[attr-defined]
        event.direction = 0.0  # type: ignore[attr-defined]

    solution = solve_ivp(
        rhs,
        (0.0, options.max_time_s),
        state0.pack(),
        method="LSODA",
        dense_output=True,
        events=(surface, seabed, dilution_limit, nonphysical, trapping, reversal),
        rtol=options.rtol,
        atol=options.atol,
    )
    if not solution.success:
        raise ModelError(f"near-field integration failed: {solution.message}")

    hard_names = (
        TerminationReason.SURFACE,
        TerminationReason.SEABED,
        TerminationReason.DILUTION_LIMIT,
        TerminationReason.NON_PHYSICAL,
    )
    events: dict[str, float] = {}
    for name, times in zip(hard_names, solution.t_events[:4], strict=True):
        if times.size:
            events[str(name)] = float(times[0])

    epsilon = 1e-8
    oscillations = sorted(
        [
            OscillationEvent(float(t), OscillationKind.TRAP)
            for t in solution.t_events[4]
            if float(t) > epsilon
        ]
        + [
            OscillationEvent(float(t), OscillationKind.REVERSAL)
            for t in solution.t_events[5]
            if float(t) > epsilon
        ]
    )

    candidates: list[tuple[float, int, TerminationReason]] = [
        (float(solution.t[-1]), 99, TerminationReason.TIME_LIMIT)
    ]
    if len(oscillations) >= options.oscillation_event_limit:
        candidates.append(
            (
                oscillations[options.oscillation_event_limit - 1].time_s,
                50,
                TerminationReason.OSCILLATION_LIMIT,
            )
        )
    if options.stop_at_surface and str(TerminationReason.SURFACE) in events:
        candidates.append((events[str(TerminationReason.SURFACE)], 10, TerminationReason.SURFACE))
    if options.stop_at_seabed and str(TerminationReason.SEABED) in events:
        candidates.append((events[str(TerminationReason.SEABED)], 10, TerminationReason.SEABED))
    if str(TerminationReason.DILUTION_LIMIT) in events:
        candidates.append(
            (
                events[str(TerminationReason.DILUTION_LIMIT)],
                20,
                TerminationReason.DILUTION_LIMIT,
            )
        )
    if str(TerminationReason.NON_PHYSICAL) in events:
        candidates.append(
            (
                events[str(TerminationReason.NON_PHYSICAL)],
                0,
                TerminationReason.NON_PHYSICAL,
            )
        )
    end_time, _priority, reason = min(candidates, key=lambda pair: (pair[0], pair[1]))
    return NearFieldSolution(
        problem=problem,
        options=options,
        reason=reason,
        end_time_s=float(end_time),
        events=events,
        oscillations=tuple(oscillations),
        geometry=geometry,
        thermodynamics=thermodynamics,
        raw_solution=solution,
    )
