from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.reference_harness.compare_examples import comparison_summary
from tools.reference_harness.plumes_dat import parse_lines


SSMC = """\
Simulation Results:
              Dilutn     P-dia    x-posn    y-posn     Depth
      Step (FluxAvg)       (m)       (m)       (m)       (m)
       250   137.648     5.144     6.256     1.994    -3.263
---------------------------- Plume traps -----------------------------
       255   147.499     5.462     6.466     2.020    -3.029
------------------------- merging happened ---------------------------
       270   165.961     6.243     6.894     2.069    -2.614
---------------------------- Plume surfaces --------------------------
       275   169.754     6.481     7.017     2.082    -2.512
-------------------- Starting Farfield Calculations --------------------
Farfield dispersion based on wastefield width of :     109.59 (m)
4/3 Power Law based Eddy Diffusivity is used:
  Dilution     Width  Distance      Time
        ()       (m)       (m)    (hrs.)
   169.754   110.588     7.320     0.016
............................. Reached Chronic Mixing Zone ..........................
   178.408   145.833   104.435     0.556
"""

EPA = SSMC.replace("109.59", "96.29").replace(
    "4/3 Power Law based Eddy Diffusivity", "Constant Eddy Diffusivity"
).replace("110.588", "96.305").replace("0.016\n", "0.000\n", 1).replace(
    "178.408   145.833   104.435     0.556",
    "175.711   124.309   104.380     0.540",
)


class PlumesDatTests(unittest.TestCase):
    def test_coordinate_contract_is_explicit(self) -> None:
        parsed = parse_lines(SSMC.splitlines())
        last = parsed.near_field[-1]
        self.assertEqual(last.z_m, -2.512)
        self.assertEqual(last.depth_below_surface_m, 2.512)
        normalized = parsed.normalized()
        self.assertEqual(
            normalized["coordinates"]["z_m"],  # type: ignore[index]
            "surface zero, positive upward",
        )

    def test_events_preserve_near_field_vs_far_field_context(self) -> None:
        parsed = parse_lines(SSMC.splitlines())
        self.assertEqual(
            [
                (
                    event.name,
                    event.section,
                    event.after_near_field_step,
                    event.after_far_field_distance_m,
                )
                for event in parsed.events
            ],
            [
                ("plume_traps", "near_field", 250, None),
                ("merging_happened", "near_field", 255, None),
                ("plume_surfaces", "near_field", 270, None),
                ("reached_chronic_mixing_zone", "far_field", None, 7.32),
            ],
        )

    def test_far_field_configuration_is_not_confused_with_near_field_change(self) -> None:
        left = parse_lines(SSMC.splitlines())
        right = parse_lines(EPA.splitlines())
        summary = comparison_summary(left, right)
        self.assertTrue(summary["near_field"]["identical_normalized_rows"])  # type: ignore[index]
        self.assertFalse(summary["far_field"]["same_diffusivity"])  # type: ignore[index]
        self.assertEqual(summary["far_field"]["left_diffusivity"], "power_4_3")  # type: ignore[index]
        self.assertEqual(summary["far_field"]["right_diffusivity"], "constant")  # type: ignore[index]

    def test_missing_simulation_table_fails_loudly(self) -> None:
        with self.assertRaisesRegex(ValueError, "no PLUMES near-field"):
            parse_lines(["Ambient Table:", "0 1 2 3"])


if __name__ == "__main__":
    unittest.main()
