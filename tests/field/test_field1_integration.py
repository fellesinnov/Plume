"""True MODEL-1 -> FIELD-1 integration checks (not a manufactured trajectory).

These tests exercise the real ODE solver, NearFieldSolution.sample and field
reconstruction. The numerical GSW branch is skipped only when the optional
runtime cannot be installed in a sandbox; the project dependency requires GSW
in a production install.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from plume.field import horizontal_plan, reconstruct_points, vertical_section
from plume.model import (
    AmbientColumn,
    AmbientLevel,
    GswThermodynamics,
    NearFieldOptions,
    NearFieldProblem,
    SeawaterState,
    SingleRoundPort,
    SourceState,
    solve_near_field,
)


class _LinearThermodynamics:
    """A deterministic equation-of-state double, NOT real seawater physics."""

    def pressure_dbar(self, depth_m: float, latitude_deg: float) -> float:
        return depth_m

    def density_kg_m3(
        self, state: SeawaterState, *, depth_m: float, latitude_deg: float
    ) -> float:
        return (1000.0 + 0.78 * state.absolute_salinity_gkg
                - 0.2 * state.conservative_temperature_C + 0.0045 * depth_m)

    def in_situ_temperature_C(
        self, state: SeawaterState, *, depth_m: float, latitude_deg: float
    ) -> float:
        return state.conservative_temperature_C


def _problem(thermo, *, real_gsw: bool) -> NearFieldProblem:
    site = {"latitude_deg": 60.0, "longitude_deg": 5.0}
    if real_gsw:
        convert = lambda depth, t: thermo.from_practical_salinity_in_situ(
            practical_salinity=35.0, in_situ_temperature_C=t,
            depth_m=depth, **site)
        ambient_levels = (
            AmbientLevel(0.0, convert(0.0, 10.0), 0.12, 0.0),
            AmbientLevel(20.0, convert(20.0, 10.0), 0.12, 0.0),
        )
        source = convert(10.0, 20.0)
    else:
        ambient_levels = (
            AmbientLevel(0.0, SeawaterState(35.0, 10.0), 0.12, 0.0),
            AmbientLevel(20.0, SeawaterState(35.0, 10.0), 0.12, 0.0),
        )
        source = SeawaterState(35.0, 20.0)
    return NearFieldProblem(
        **site, water_depth_m=20.0,
        port=SingleRoundPort(
            diameter_m=0.2,
            discharge_depth_below_surface_m=10.0,
            vertical_angle_deg=15.0,
            azimuth_deg=90.0,
        ),
        source=SourceState(flow_m3s=0.05, seawater=source),
        ambient=AmbientColumn.from_levels(ambient_levels),
    )


def _run_and_check(thermo, *, real_gsw: bool):
    solution = solve_near_field(
        _problem(thermo, real_gsw=real_gsw),
        thermodynamics=thermo,
        options=NearFieldOptions(max_time_s=0.7, oscillation_event_limit=20),
    )
    assert 0.1 < solution.end_time_s <= 0.7
    trace = solution.sample(np.linspace(0.0, solution.end_time_s, 70))
    assert np.all(np.isfinite(trace.excess_temperature_C))
    assert np.all(np.diff(trace.time_s) > 0)
    assert trace.dilution[-1] > trace.dilution[0]

    # Evaluate field at ACTUAL solved 3-D centerline points. No fabricated
    # shape or 2-D centerline projection is allowed.
    sampled = reconstruct_points(
        trace, ambient=solution.problem.ambient, thermodynamics=thermo,
        latitude_deg=solution.problem.latitude_deg,
        water_depth_m=solution.problem.water_depth_m,
        east_m=trace.x_east_m, north_m=trace.y_north_m,
        depth_m=trace.depth_m,
        chunk_size=7,
    )
    assert sampled.modeled.all()
    assert np.isfinite(sampled.delta_temperature_C).all()
    assert (sampled.delta_temperature_C > 0).all()
    assert sampled.delta_temperature_C[0] == pytest.approx(10.0, abs=2e-6)
    assert float(sampled.delta_temperature_C.max()) <= 10.2

    # Near-source support is finite; off-center or downstream cannot be
    # quietly counted as measured zero.
    out = reconstruct_points(
        trace, ambient=solution.problem.ambient, thermodynamics=thermo,
        latitude_deg=60.0, water_depth_m=20.0,
        east_m=-2.0, north_m=2.0, depth_m=10.0,
    )
    assert not bool(out.modeled)
    assert float(out.delta_temperature_C) == 0.0

    section = vertical_section(
        solution, distances_m=np.linspace(-0.3, 5.0, 111),
        depths_m=np.linspace(7.0, 12.0, 91),
        heading_deg=90.0, samples=110,
    )
    plan = horizontal_plan(
        solution, east_m=np.linspace(-0.3, 5.0, 111),
        north_m=np.linspace(-0.8, 0.8, 73),
        depth_m=10.0, samples=110,
    )
    assert section.values.modeled.any()
    assert plan.values.modeled.any()
    assert float(section.values.delta_temperature_C.max()) > 0.0
    assert float(plan.values.delta_temperature_C.max()) > 0.0
    assert section.values.delta_temperature_C.shape == (91, 111)
    assert plan.values.delta_temperature_C.shape == (73, 111)
    assert section.heading_or_depth == pytest.approx(90.0)
    assert plan.heading_or_depth == 10.0
    return solution, section, plan


def test_complete_model_field_seam_with_injected_deterministic_thermo():
    _run_and_check(_LinearThermodynamics(), real_gsw=False)


def test_live_gsw_numeric_roundtrip_and_full_model_field_seam():
    gsw = pytest.importorskip("gsw", reason="official GSW package not available")
    thermo = GswThermodynamics(gsw)
    p = thermo.pressure_dbar(10.0, 60.0)
    assert math.isfinite(p) and 9.0 < p < 12.0
    state = thermo.from_practical_salinity_in_situ(
        practical_salinity=35.0, in_situ_temperature_C=10.0,
        depth_m=10.0, latitude_deg=60.0, longitude_deg=5.0)
    assert 34.0 < state.absolute_salinity_gkg < 36.5
    assert 8.0 < state.conservative_temperature_C < 11.0
    rho = thermo.density_kg_m3(
        state, depth_m=10.0, latitude_deg=60.0)
    assert 1015.0 < rho < 1050.0
    assert thermo.in_situ_temperature_C(
        state, depth_m=10.0, latitude_deg=60.0) == pytest.approx(10.0, abs=2e-10)
    _run_and_check(thermo, real_gsw=True)
