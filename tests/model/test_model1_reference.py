"""Small derived software-reference checks for the MODEL-1 kernel.

These samples are transcribed from Ebb Carbon ``Plumes_Public`` reference
cases at pinned commit 9791c80ff94f706603df0ae473667ccdffd359db.  They are
software-regression evidence only, not physical validation.  The full raw
third-party/reference evidence remains outside the product kernel.
"""

from __future__ import annotations

import unittest

import numpy as np

from plume.model import (
    AmbientColumn,
    AmbientLevel,
    NearFieldOptions,
    NearFieldProblem,
    SeawaterState,
    OscillationKind,
    SingleRoundPort,
    SourceState,
    TerminationReason,
    solve_near_field,
)


class LegacyKnudsenThermodynamics:
    """Reference-only Knudsen EOS; never a production thermodynamic fallback.

    For this compatibility test the ``SeawaterState`` slots deliberately carry
    the legacy trace's practical-salinity / temperature scalars.  Production
    code instead receives TEOS-10 Absolute Salinity / Conservative Temperature.
    """

    def pressure_dbar(self, depth_m: float, latitude_deg: float) -> float:
        del depth_m, latitude_deg
        return 0.0

    def density_kg_m3(
        self,
        state: SeawaterState,
        *,
        depth_m: float,
        latitude_deg: float,
    ) -> float:
        del depth_m, latitude_deg
        s = state.absolute_salinity_gkg
        t = state.conservative_temperature_C
        sigma_zero = -0.093 + 0.8149 * s - 0.000482 * s**2 + 0.0000068 * s**3
        pure = -((t - 3.98) ** 2) * (t + 283.0) / (503.570 * (t + 67.26))
        a_t = t * (4.7867 - 0.098185 * t + 0.0010843 * t**2) * 1e-3
        b_t = t * (18.030 - 0.8164 * t + 0.01667 * t**2) * 1e-6
        return 1000.0 + pure + (sigma_zero + 0.1324) * (
            1.0 - a_t + b_t * (sigma_zero - 0.1324)
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


THERMO = LegacyKnudsenThermodynamics()
AMBIENT_VALUES = (
    (0.0, 30.9, 11.2),
    (3.0, 31.2, 10.4),
    (6.0, 31.2, 9.69),
    (9.0, 31.7, 9.44),
    (12.0, 31.8, 9.34),
    (15.0, 31.9, 9.22),
    # The archived table ends at 15 m while the bottom is 17 m.  The early-jet
    # samples below stay near 2 m; this explicit final level only satisfies the
    # product kernel's no-hidden-extrapolation boundary contract.
    (17.0, 31.9, 9.22),
)
REFERENCE_DILUTION = np.array([2.003, 2.697, 4.009, 5.958, 7.264, 8.855, 10.795])


def reference_problem(current_mps: float) -> NearFieldProblem:
    levels = AmbientColumn.from_levels(
        AmbientLevel(
            depth,
            SeawaterState(salinity, temperature),
            0.0,
            current_mps,
        )
        for depth, salinity, temperature in AMBIENT_VALUES
    )
    return NearFieldProblem(
        latitude_deg=45.0,
        longitude_deg=0.0,
        water_depth_m=17.0,
        # PLUMES/Ebb H-angle 90 deg points along their +y axis.  Plume's ENU
        # equivalent is navigation azimuth 0 deg (north / +y).
        port=SingleRoundPort(0.0127, 2.0, 45.0, 0.0),
        source=SourceState(5.0e-5, SeawaterState(35.0, 10.0)),
        ambient=levels,
    )


def solve_reference(current_mps: float):
    return solve_near_field(
        reference_problem(current_mps),
        thermodynamics=THERMO,
        options=NearFieldOptions(
            contraction_coefficient=0.61,
            aspiration_coefficient=0.10,
            max_time_s=10.0,
            oscillation_event_limit=20,
            stop_at_surface=False,
        ),
    )


class EbbSoftwareReferenceTests(unittest.TestCase):
    def test_source_contraction_matches_the_decoded_single_port_relation(self) -> None:
        solution = solve_reference(0.0)
        start = solution.sample([0.0])
        expected_diameter = 0.0127 * np.sqrt(0.61)
        expected_speed = 5.0e-5 / (0.61 * np.pi * (0.0127 / 2.0) ** 2)
        self.assertAlmostEqual(start.diameter_m[0], expected_diameter, places=10)
        self.assertAlmostEqual(start.speed_mps[0], expected_speed, places=10)

    def test_zero_current_jet_meets_the_existing_half_percent_reference_bar(self) -> None:
        # Selected test23 rows 35/50/70/90/100/110/120.  Ebb's qualification
        # already uses 0.5 % jet-phase MARE; Plume reuses that named software
        # reference bar rather than inventing a new tolerance for this fixture.
        times = np.array([0.058, 0.120, 0.290, 0.670, 1.013, 1.535, 2.335])
        ours = solve_reference(0.0).sample(times).dilution
        relative = np.abs(ours - REFERENCE_DILUTION) / REFERENCE_DILUTION
        self.assertLess(float(relative.mean()), 0.005)
        self.assertLess(float(relative.max()), 0.015)

    def test_current_aware_reference_closure_meets_same_bar_at_001_mps(self) -> None:
        # Selected case19/test28 rows at the same dilution checkpoints.
        times = np.array([0.057, 0.118, 0.282, 0.636, 0.948, 1.407, 2.085])
        ours = solve_reference(0.01).sample(times).dilution
        relative = np.abs(ours - REFERENCE_DILUTION) / REFERENCE_DILUTION
        self.assertLess(float(relative.mean()), 0.005)
        self.assertLess(float(relative.max()), 0.015)

    def test_reference_trap_reversal_sequence_stops_on_fourth_oscillation_event(self) -> None:
        solution = solve_near_field(
            reference_problem(0.0),
            thermodynamics=THERMO,
            options=NearFieldOptions(
                contraction_coefficient=0.61,
                aspiration_coefficient=0.10,
                max_time_s=300.0,
                max_dilution=1.0e6,
                oscillation_event_limit=4,
                stop_at_surface=False,
                stop_at_seabed=False,
            ),
        )
        self.assertEqual(solution.reason, TerminationReason.OSCILLATION_LIMIT)
        first_four = [event.kind for event in solution.oscillations[:4]]
        self.assertEqual(
            first_four,
            [
                OscillationKind.REVERSAL,
                OscillationKind.TRAP,
                OscillationKind.REVERSAL,
                OscillationKind.TRAP,
            ],
        )
        self.assertAlmostEqual(solution.end_time_s, solution.oscillations[3].time_s)


if __name__ == "__main__":
    unittest.main()
