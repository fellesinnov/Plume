#!/usr/bin/env python3
"""Small regression/sanity test suite for outfall_screen.py."""

import math
from outfall_screen import (
    OutfallCase, seawater_density_eos80, simulate, source_properties
)

def check(cond, msg):
    if not cond:
        raise AssertionError(msg)

def main():
    # EOS basic behavior at marine salinity.
    rho20 = seawater_density_eos80(20, 35)
    rho30 = seawater_density_eos80(30, 35)
    check(rho30 < rho20, "Warm seawater should be less dense than cooler seawater at same salinity.")

    # Same-seawater +10C source should be positively buoyant.
    c = OutfallCase(4000, 0.8, 20, 10, water_depth_m=15,
                    port_height_m=1.6, vertical_angle_deg=15)
    src = source_properties(c)
    check(src["gprime0_mps2"] > 0, "Warm seawater source should have positive reduced gravity.")
    check(abs(src["velocity0_mps"] - 2.2105) < 0.01, "Unexpected baseline outlet velocity.")

    # Scalar conservation: in a uniform ambient the bulk excess T must be dT/S_bulk.
    r = simulate(c)
    p = r["profile"]
    max_err = abs(p["bulk_delta_T_C"] - c.delta_T_C/p["dilution_bulk"]).max()
    check(max_err < 1e-10, "Bulk thermal dilution identity failed.")

    # More water depth should increase available path/dilution for the same source geometry.
    r15 = simulate(c)
    r30 = simulate(OutfallCase(4000, 0.8, 20, 10, water_depth_m=30,
                               port_height_m=1.6, vertical_angle_deg=15))
    check(
        r30["summary"]["termination_centerline_dilution"] >
        r15["summary"]["termination_centerline_dilution"],
        "Deeper-water sanity trend failed."
    )

    # A high-momentum, deeply submerged example should pass the proposed GREEN screen.
    rg = simulate(OutfallCase(4000, 0.4, 20, 10, water_depth_m=30,
                              port_height_m=1.0, vertical_angle_deg=15))
    check(rg["summary"]["status"] == "GREEN", "Known GREEN regression case changed.")

    print("All self-tests passed.")
    print("Baseline status:", r["summary"]["status"],
          "| end centerline dilution:", round(r["summary"]["termination_centerline_dilution"], 3))
    print("GREEN regression status:", rg["summary"]["status"],
          "| end centerline dilution:", round(rg["summary"]["termination_centerline_dilution"], 3))

if __name__ == "__main__":
    main()
