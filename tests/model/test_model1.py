from __future__ import annotations

import math
import unittest

import numpy as np

from plume.errors import (
    ModelInputError,
    ThermodynamicsError,
    UnsupportedModelOutletError,
)
from plume.model import (
    AmbientColumn,
    AmbientLevel,
    ClosureKind,
    GswThermodynamics,
    NearFieldOptions,
    NearFieldProblem,
    SeawaterState,
    SingleRoundPort,
    SourceState,
    Um3ReferenceEntrainment,
    build_near_field_port,
    projected_area,
    solve_near_field,
    taylor_area,
    vertical_plane_frame,
)


class LinearThermodynamics:
    """Deterministic test double; not a physical seawater equation of state."""

    def pressure_dbar(self, depth_m: float, latitude_deg: float) -> float:
        del latitude_deg
        return float(depth_m)

    def density_kg_m3(
        self,
        state: SeawaterState,
        *,
        depth_m: float,
        latitude_deg: float,
    ) -> float:
        del latitude_deg
        return (
            1000.0
            + 0.78 * state.absolute_salinity_gkg
            - 0.20 * state.conservative_temperature_C
            + 0.0045 * depth_m
        )

    def in_situ_temperature_C(
        self,
        state: SeawaterState,
        *,
        depth_m: float,
        latitude_deg: float,
    ) -> float:
        del depth_m, latitude_deg
        return state.conservative_temperature_C


THERMO = LinearThermodynamics()


def ambient(
    *,
    water_depth: float = 20.0,
    top_sa: float = 35.0,
    bottom_sa: float = 35.0,
    top_ct: float = 10.0,
    bottom_ct: float = 10.0,
    top_u: float = 0.0,
    bottom_u: float = 0.0,
) -> AmbientColumn:
    return AmbientColumn.from_levels(
        [
            AmbientLevel(0.0, SeawaterState(top_sa, top_ct), top_u, 0.0),
            AmbientLevel(
                water_depth,
                SeawaterState(bottom_sa, bottom_ct),
                bottom_u,
                0.0,
            ),
        ]
    )


def problem(
    *,
    source_sa: float = 35.0,
    source_ct: float = 20.0,
    flow: float = 0.05,
    vertical: float = 20.0,
    azimuth: float = 90.0,
    depth: float = 10.0,
    diameter: float = 0.2,
    amb: AmbientColumn | None = None,
) -> NearFieldProblem:
    amb = amb or ambient()
    return NearFieldProblem(
        latitude_deg=60.0,
        longitude_deg=5.0,
        water_depth_m=amb.maximum_depth_m,
        port=SingleRoundPort(diameter, depth, vertical, azimuth),
        source=SourceState(flow, SeawaterState(source_sa, source_ct)),
        ambient=amb,
    )


class ContractTests(unittest.TestCase):
    def test_navigation_azimuth_maps_to_enu(self) -> None:
        north = SingleRoundPort(1.0, 5.0, 0.0, 0.0).velocity_vector(2.0)
        east = SingleRoundPort(1.0, 5.0, 0.0, 90.0).velocity_vector(2.0)
        up = SingleRoundPort(1.0, 5.0, 90.0, 123.0).velocity_vector(2.0)
        np.testing.assert_allclose(north, [0.0, 2.0, 0.0], atol=1e-12)
        np.testing.assert_allclose(east, [2.0, 0.0, 0.0], atol=1e-12)
        np.testing.assert_allclose(up, [0.0, 0.0, 2.0], atol=1e-12)

    def test_non_finite_model_inputs_fail_deterministically(self) -> None:
        with self.assertRaisesRegex(ModelInputError, "finite"):
            SingleRoundPort(float("nan"), 5.0, 0.0, 0.0)
        with self.assertRaisesRegex(ModelInputError, "finite"):
            SeawaterState(35.0, float("nan"))

    def test_ambient_requires_explicit_full_water_column(self) -> None:
        with self.assertRaisesRegex(ModelInputError, "full water column"):
            NearFieldProblem(
                latitude_deg=60.0,
                longitude_deg=5.0,
                water_depth_m=20.0,
                port=SingleRoundPort(0.2, 10.0, 0.0, 0.0),
                source=SourceState(0.05, SeawaterState(35.0, 10.0)),
                ambient=AmbientColumn.from_levels(
                    [
                        AmbientLevel(2.0, SeawaterState(35.0, 10.0)),
                        AmbientLevel(20.0, SeawaterState(35.0, 10.0)),
                    ]
                ),
            )

    def test_ambient_interpolates_thermodynamics_and_current_by_depth(self) -> None:
        column = ambient(
            top_sa=34.0,
            bottom_sa=36.0,
            top_ct=12.0,
            bottom_ct=8.0,
            top_u=0.0,
            bottom_u=0.2,
        )
        sample = column.sample(
            5.0,
            water_depth_m=20.0,
            latitude_deg=60.0,
            thermodynamics=THERMO,
        )
        self.assertAlmostEqual(sample.seawater.absolute_salinity_gkg, 34.5)
        self.assertAlmostEqual(sample.seawater.conservative_temperature_C, 11.0)
        self.assertAlmostEqual(sample.velocity_mps[0], 0.05)


    def test_normalized_single_round_port_has_an_explicit_physics_adapter(self) -> None:
        port = build_near_field_port(
            {
                "type": "single_round_port",
                "diameter_m": 0.8,
                "discharge_depth_below_surface_m": 12.0,
                "vertical_angle_deg": 5.0,
                "azimuth_deg": 90.0,
            }
        )
        self.assertEqual(port.diameter_m, 0.8)
        self.assertEqual(port.azimuth_deg, 90.0)

    def test_representable_but_unimplemented_outlet_fails_at_model_boundary(self) -> None:
        with self.assertRaisesRegex(UnsupportedModelOutletError, "no MODEL-1"):
            build_near_field_port({"type": "future_multiport"})

    def test_initial_contracted_element_must_fit_between_boundaries(self) -> None:
        with self.assertRaisesRegex(ModelInputError, "free surface"):
            solve_near_field(
                problem(depth=0.02, diameter=0.2),
                thermodynamics=THERMO,
                options=NearFieldOptions(max_time_s=1.0),
            )


class EntrainmentTests(unittest.TestCase):
    def test_vertical_plane_keeps_cross_current_in_plane(self) -> None:
        rising = np.array([0.0, 0.0, 2.0])
        current = np.array([0.05, 0.0, 0.0])
        frame = vertical_plane_frame(rising, current)
        along, in_plane, out = frame.components(current)
        self.assertAlmostEqual(along, 0.0, places=12)
        self.assertAlmostEqual(abs(in_plane), 0.05, places=12)
        self.assertAlmostEqual(out, 0.0, places=12)

    def test_um3_reference_reduces_to_taylor_in_still_water(self) -> None:
        plume = np.array([0.0, 0.3, 0.4])
        closure = Um3ReferenceEntrainment()
        total = closure.rate_kg_s(
            ambient_density_kg_m3=1024.0,
            ambient_velocity_mps=np.zeros(3),
            plume_velocity_mps=plume,
            radius_m=0.5,
            thickness_m=0.2,
            radius_gradient=0.1,
            elevation_gradient=0.05,
            aspiration_coefficient=0.1,
        )
        expected = 1024.0 * taylor_area(0.5, 0.2) * 0.1 * 0.5
        self.assertAlmostEqual(total, expected, places=12)

    def test_um3_taylor_cylinder_pair_cancels_in_weak_crossflow(self) -> None:
        alpha, radius, thickness = 0.1, 0.5, 0.2
        plume = np.array([0.0, 0.6, 0.6])
        ambient_current = np.array([0.0, 0.02, 0.0])
        frame = vertical_plane_frame(plume, ambient_current)
        in_plane = ambient_current - np.dot(ambient_current, frame.out_of_plane) * frame.out_of_plane
        along = float(np.dot(in_plane, frame.along))
        speed = float(np.linalg.norm(plume))
        across = float(np.linalg.norm(in_plane)) * abs(plume[2]) / speed
        shear = alpha * abs(speed - along)
        self.assertLess(across, shear)
        reduced = taylor_area(radius, thickness) * (shear - across / math.pi)
        cylinder = projected_area(radius, thickness, 0.0, 0.0).cylinder_m2 * across
        self.assertAlmostEqual(
            reduced + cylinder,
            taylor_area(radius, thickness) * shear,
            places=12,
        )

    def test_published_curvature_area_is_signed(self) -> None:
        rising = projected_area(0.5, 0.2, 0.1, +0.3)
        falling = projected_area(0.5, 0.2, 0.1, -0.3)
        self.assertLess(rising.curvature_m2, 0.0)
        self.assertGreater(falling.curvature_m2, 0.0)


class SolverTests(unittest.TestCase):
    def test_dilution_grows_and_heat_salt_mix_conservatively(self) -> None:
        p = problem(
            source_sa=36.0,
            source_ct=20.0,
            amb=ambient(top_sa=34.0, bottom_sa=34.0, top_ct=10.0, bottom_ct=10.0),
        )
        solution = solve_near_field(
            p,
            thermodynamics=THERMO,
            options=NearFieldOptions(max_time_s=1.0, oscillation_event_limit=20),
        )
        end = min(solution.end_time_s, 0.5)
        trajectory = solution.sample(np.linspace(0.0, end, 21))
        self.assertGreater(trajectory.dilution[-1], trajectory.dilution[0])
        self.assertTrue(np.all(np.diff(trajectory.dilution) >= -1e-10))
        dilution = float(trajectory.dilution[-1])
        expected_sa = (36.0 + (dilution - 1.0) * 34.0) / dilution
        expected_ct = (20.0 + (dilution - 1.0) * 10.0) / dilution
        self.assertAlmostEqual(trajectory.absolute_salinity_gkg[-1], expected_sa, places=7)
        self.assertAlmostEqual(trajectory.conservative_temperature_C[-1], expected_ct, places=7)

    def test_freshwater_source_is_valid_and_mixes_upward_from_zero_salinity(self) -> None:
        p = problem(
            source_sa=0.0,
            source_ct=10.0,
            amb=ambient(top_sa=35.0, bottom_sa=35.0),
        )
        solution = solve_near_field(
            p,
            thermodynamics=THERMO,
            options=NearFieldOptions(max_time_s=0.3, oscillation_event_limit=20),
        )
        trajectory = solution.sample([0.0, min(0.2, solution.end_time_s)])
        self.assertEqual(trajectory.absolute_salinity_gkg[0], 0.0)
        self.assertGreaterEqual(trajectory.absolute_salinity_gkg[-1], 0.0)
        self.assertGreater(trajectory.absolute_salinity_gkg[-1], 0.0)

    def test_warmer_lighter_source_rises_more_than_neutral_source(self) -> None:
        neutral_problem = problem(source_ct=10.0, vertical=0.0)
        warm_problem = problem(source_ct=20.0, vertical=0.0)
        opts = NearFieldOptions(max_time_s=1.0, oscillation_event_limit=20)
        neutral = solve_near_field(neutral_problem, thermodynamics=THERMO, options=opts)
        warm = solve_near_field(warm_problem, thermodynamics=THERMO, options=opts)
        time = min(neutral.end_time_s, warm.end_time_s, 0.7)
        neutral_z = neutral.sample([time]).z_up_m[0]
        warm_z = warm.sample([time]).z_up_m[0]
        self.assertGreater(warm_z, neutral_z)

    def test_cross_current_bends_trajectory_downstream(self) -> None:
        still = problem(azimuth=0.0, amb=ambient(top_u=0.0, bottom_u=0.0))
        moving = problem(azimuth=0.0, amb=ambient(top_u=0.15, bottom_u=0.15))
        opts = NearFieldOptions(max_time_s=1.0, oscillation_event_limit=20)
        still_s = solve_near_field(still, thermodynamics=THERMO, options=opts)
        moving_s = solve_near_field(moving, thermodynamics=THERMO, options=opts)
        time = min(still_s.end_time_s, moving_s.end_time_s, 0.7)
        self.assertGreater(
            moving_s.sample([time]).x_east_m[0],
            still_s.sample([time]).x_east_m[0] + 1e-5,
        )

    def test_vertical_jet_begins_bending_under_cross_current(self) -> None:
        p = problem(
            vertical=90.0,
            azimuth=0.0,
            amb=ambient(top_u=0.15, bottom_u=0.15),
        )
        solution = solve_near_field(
            p,
            thermodynamics=THERMO,
            options=NearFieldOptions(
                closure=ClosureKind.PUBLISHED_PAE,
                max_time_s=0.4,
                oscillation_event_limit=20,
            ),
        )
        sample = solution.sample([min(0.2, solution.end_time_s)])
        self.assertGreater(sample.x_east_m[0], 0.0)
        self.assertTrue(np.isfinite(sample.dilution[0]))

    def test_depth_varying_current_changes_path_relative_to_constant_current(self) -> None:
        constant = ambient(top_u=0.0, bottom_u=0.0)
        sheared = ambient(top_u=0.25, bottom_u=0.0)
        p0 = problem(azimuth=0.0, depth=10.0, amb=constant)
        p1 = problem(azimuth=0.0, depth=10.0, amb=sheared)
        opts = NearFieldOptions(max_time_s=1.0, oscillation_event_limit=20)
        s0 = solve_near_field(p0, thermodynamics=THERMO, options=opts)
        s1 = solve_near_field(p1, thermodynamics=THERMO, options=opts)
        time = min(s0.end_time_s, s1.end_time_s, 0.7)
        self.assertGreater(s1.sample([time]).x_east_m[0], s0.sample([time]).x_east_m[0])

    def test_surface_contact_is_an_edge_event(self) -> None:
        p = problem(source_ct=35.0, vertical=70.0, depth=1.0, diameter=0.1, flow=0.02)
        solution = solve_near_field(
            p,
            thermodynamics=THERMO,
            options=NearFieldOptions(max_time_s=30.0, oscillation_event_limit=20),
        )
        self.assertEqual(solution.reason.value, "surface")
        final = solution.sample([solution.end_time_s])
        self.assertAlmostEqual(
            final.depth_m[0] - 0.5 * final.diameter_m[0],
            0.0,
            places=5,
        )

    def test_closure_candidates_are_distinct_in_crossflow(self) -> None:
        p = problem(amb=ambient(top_u=0.1, bottom_u=0.1))
        common = dict(max_time_s=0.8, oscillation_event_limit=20)
        um3 = solve_near_field(
            p,
            thermodynamics=THERMO,
            options=NearFieldOptions(closure=ClosureKind.UM3_REFERENCE, **common),
        )
        pae = solve_near_field(
            p,
            thermodynamics=THERMO,
            options=NearFieldOptions(closure=ClosureKind.PUBLISHED_PAE, **common),
        )
        time = min(um3.end_time_s, pae.end_time_s, 0.6)
        self.assertGreater(
            abs(float(um3.sample([time]).dilution[0] - pae.sample([time]).dilution[0])),
            1e-5,
        )


class GswBoundaryTests(unittest.TestCase):
    def test_missing_gsw_fails_explicitly_instead_of_falling_back(self) -> None:
        try:
            import gsw  # noqa: F401
        except ImportError:
            with self.assertRaisesRegex(ThermodynamicsError, "TEOS-10"):
                GswThermodynamics()
        else:
            self.assertIsNotNone(GswThermodynamics())


if __name__ == "__main__":
    unittest.main()

class AdditionalSolverEvidenceTests(unittest.TestCase):
    def test_seabed_contact_is_an_edge_event(self) -> None:
        p = problem(
            source_sa=38.0,
            source_ct=5.0,
            vertical=-70.0,
            depth=19.0,
            diameter=0.1,
            flow=0.02,
        )
        solution = solve_near_field(
            p,
            thermodynamics=THERMO,
            options=NearFieldOptions(max_time_s=30.0, oscillation_event_limit=20),
        )
        self.assertEqual(solution.reason.value, "seabed")
        final = solution.sample([solution.end_time_s])
        self.assertAlmostEqual(
            final.depth_m[0] + 0.5 * final.diameter_m[0],
            p.water_depth_m,
            places=5,
        )

    def test_default_solver_tolerance_is_converged_against_tighter_control(self) -> None:
        p = problem(amb=ambient(top_u=0.1, bottom_u=0.1))
        normal = solve_near_field(
            p,
            thermodynamics=THERMO,
            options=NearFieldOptions(
                max_time_s=1.0,
                oscillation_event_limit=20,
                rtol=1e-6,
                atol=1e-9,
            ),
        )
        tight = solve_near_field(
            p,
            thermodynamics=THERMO,
            options=NearFieldOptions(
                max_time_s=1.0,
                oscillation_event_limit=20,
                rtol=1e-8,
                atol=1e-11,
            ),
        )
        time = min(normal.end_time_s, tight.end_time_s, 0.8)
        normal_t = normal.sample([time])
        tight_t = tight.sample([time])
        for name in ("dilution", "diameter_m", "x_east_m", "z_up_m"):
            observed = float(getattr(normal_t, name)[0])
            control = float(getattr(tight_t, name)[0])
            self.assertLess(
                abs(observed - control) / max(abs(control), 1e-12),
                2e-6,
                name,
            )


class FakeGsw:
    def p_from_z(self, z: float, latitude: float) -> float:
        return -z + latitude * 0.0

    def SA_from_SP(self, sp: float, pressure: float, longitude: float, latitude: float) -> float:
        return sp + 0.1 + 0.0 * (pressure + longitude + latitude)

    def CT_from_t(self, sa: float, temperature: float, pressure: float) -> float:
        return temperature - 0.2 + 0.0 * (sa + pressure)

    def rho(self, sa: float, ct: float, pressure: float) -> float:
        return 1000.0 + sa - 0.2 * ct + 0.01 * pressure

    def t_from_CT(self, sa: float, ct: float, pressure: float) -> float:
        return ct + 0.2 + 0.0 * (sa + pressure)


class GswContractTests(unittest.TestCase):
    def test_gsw_adapter_normalizes_sp_and_in_situ_temperature_before_kernel(self) -> None:
        thermo = GswThermodynamics(FakeGsw())
        state = thermo.from_practical_salinity_in_situ(
            practical_salinity=35.0,
            in_situ_temperature_C=12.0,
            depth_m=10.0,
            latitude_deg=60.0,
            longitude_deg=5.0,
        )
        self.assertAlmostEqual(state.absolute_salinity_gkg, 35.1)
        self.assertAlmostEqual(state.conservative_temperature_C, 11.8)
        self.assertAlmostEqual(thermo.pressure_dbar(10.0, 60.0), 10.0)
        self.assertAlmostEqual(
            thermo.in_situ_temperature_C(state, depth_m=10.0, latitude_deg=60.0),
            12.0,
        )
        self.assertAlmostEqual(
            thermo.density_kg_m3(state, depth_m=10.0, latitude_deg=60.0),
            1032.84,
        )
