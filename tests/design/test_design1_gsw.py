"""DESIGN-1 exact-provider-no-refetch discriminator against official GSW.

Runs the REAL MODEL-1 -> FIELD-1 -> Matplotlib path. Synthetic inline data
and source design choices are not physical validation or permit evidence.
"""
from __future__ import annotations

import copy
import math
from unittest.mock import patch

import numpy as np
import pytest

from plume.config import LoadedConfig, load_config, normalize_config
from plume.design import candidate_config, evaluate_design, pin_snapshot
from plume.design.snapshot import _digest
from plume.render import render_field_pair


def test_live_gsw_two_design_variants_and_computed_png_no_provider_refetch(tmp_path):
    pytest.importorskip("gsw", reason="official GSW-Python is required for numeric DESIGN-1 closure")
    pytest.importorskip("matplotlib", reason="Matplotlib is required for DESIGN-1 plots")

    # Match the synthetic-instrumented FIELD-1 diagnostic's known operating
    # envelope; no external ocean API or physical calibration is involved.
    example = load_config("configs/example.yaml")
    raw = copy.deepcopy(example.normalized)
    raw["site"]["water_depth_m"] = 25.0
    raw["outfall"].update({
        "diameter_m": 0.35,
        "discharge_depth_below_surface_m": 12.0,
        "vertical_angle_deg": 15.0,
        "azimuth_deg": 90.0,
    })
    raw["forcing"]["source"] = {
        "flow_m3h": {"provider": "constant", "value": 540.0},
        "delta_T_C": {"provider": "constant", "value": 10.0},
        "salinity_psu": {"provider": "constant", "value": 35.0},
    }
    raw["forcing"]["ambient"] = {
        "temperature_profile_C": {"provider": "inline_profile", "levels": [
            {"depth_m": 0.0, "value": 13.0},
            {"depth_m": 10.0, "value": 11.5},
            {"depth_m": 25.0, "value": 9.0},
        ]},
        "salinity_profile_psu": {"provider": "inline_profile", "levels": [
            {"depth_m": 0.0, "value": 34.7},
            {"depth_m": 10.0, "value": 34.9},
            {"depth_m": 25.0, "value": 35.0},
        ]},
        "current_profile": {"provider": "constant_vector",
                            "u_east_mps": 0.12, "v_north_mps": 0.0},
    }
    raw["model"]["near_field"] = {"enabled": True, "options": {
        "max_time_s": 8.0, "oscillation_event_limit": 20,
    }}
    normalized = normalize_config(raw)
    config = LoadedConfig(example.source_path, normalized, _digest(normalized))

    from plume.design import snapshot as snapshot_module
    with patch.object(snapshot_module, "load_provider", wraps=snapshot_module.load_provider) as provider:
        pinned = pin_snapshot(config)
        assert provider.call_count == 6  # flow, process delta, source SP + T, SP, current
        first = evaluate_design(config.normalized, pinned,
                                section_resolution=(51, 41), plan_resolution=(51, 41))
        variant = candidate_config(config.normalized, depth_m=12.0, diameter_m=0.50,
                                   angle_deg=25.0, azimuth_deg=90.0,
                                   flow_m3h=540.0, delta_T_C=10.0)
        second = evaluate_design(variant, pinned,
                                 section_resolution=(51, 41), plan_resolution=(51, 41))
        assert provider.call_count == 6  # geometry edits never reach any provider

    assert first.snapshot.snapshot_sha256 == second.snapshot.snapshot_sha256
    assert first.config_sha256 != second.config_sha256
    assert first.section.values.modeled.any() and second.section.values.modeled.any()
    assert first.plan.values.modeled.any() and second.plan.values.modeled.any()
    for evaluated in (first, second):
        assert evaluated.metrics["model_status"].startswith("UNVALIDATED")
        assert evaluated.metrics["criterion_status"].startswith("NOT_ASSESSED")
        assert math.isfinite(evaluated.metrics["final_bulk_dilution"])
        assert np.isfinite(evaluated.section.values.delta_temperature_C).all()
        assert np.isfinite(evaluated.plan.values.delta_temperature_C).all()
        assert evaluated.section.values.delta_temperature_C.max() > 0.0
        assert evaluated.plan.values.delta_temperature_C.max() > 0.0

    # Render the SOLVED field pair, not an illustrative, fabricated trajectory.
    fig = render_field_pair(first.section, first.plan,
                            threshold_delta_T_C=first.metrics["threshold_delta_T_C"],
                            title="DESIGN-1 official GSW synthetic case (UNVALIDATED)")
    try:
        output = tmp_path / "design1-actual-solver-gsw.png"
        fig.savefig(output, dpi=100, facecolor=fig.get_facecolor())
        assert output.stat().st_size > 8000
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)
