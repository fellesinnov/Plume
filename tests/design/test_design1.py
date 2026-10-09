"""DESIGN-1 structural and real MODEL/FIELD seam tests (synthetic water only)."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from plume.config import LoadedConfig, normalize_config
from plume.design import ProjectStore, candidate_config, evaluate_design, pin_snapshot
from plume.design.snapshot import PinnedSnapshot, _digest
from plume.errors import ModelInputError, ProviderDataError, WorkspaceError
from plume.model import SeawaterState
from plume.providers import ProviderContext, load_provider, normalize_provider_spec


class LinearThermo:
    """Injected deterministic test double, NOT seawater thermodynamics."""

    def from_practical_salinity_in_situ(self, *, practical_salinity, in_situ_temperature_C,
                                        depth_m, latitude_deg, longitude_deg):
        return SeawaterState(practical_salinity, in_situ_temperature_C)

    def pressure_dbar(self, depth_m, latitude_deg):
        return depth_m

    def density_kg_m3(self, state, *, depth_m, latitude_deg):
        return (1000.0 + 0.78 * state.absolute_salinity_gkg
                - 0.20 * state.conservative_temperature_C + 0.0045 * depth_m)

    def in_situ_temperature_C(self, state, *, depth_m, latitude_deg):
        return state.conservative_temperature_C


def _template(tmp_path):
    raw = {
        "schema_version": 1,
        "project": {"id": "demo", "name": "Demo"},
        "site": {"latitude_deg": 60, "longitude_deg": 5, "water_depth_m": 25},
        "outfall": {"type": "single_round_port", "diameter_m": 0.35,
                    "discharge_depth_below_surface_m": 12,
                    "vertical_angle_deg": 15, "azimuth_deg": 90},
        "forcing": {
            "clock": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z", "step": "PT1H"},
            "source": {"flow_m3h": {"provider": "constant", "value": 540},
                       "delta_T_C": {"provider": "constant", "value": 10}},
            "ambient": {"temperature_profile_C": {"provider": "inline_profile", "levels": [
                           {"depth_m": 0, "value": 13}, {"depth_m": 10, "value": 11.5},
                           {"depth_m": 25, "value": 9}]},
                        "salinity_profile_psu": {"provider": "inline_profile", "levels": [
                           {"depth_m": 0, "value": 34.7}, {"depth_m": 25, "value": 35}]},
                        "current_profile": {"provider": "constant_vector", "u_east_mps": .12,
                                            "v_north_mps": 0}},
        },
        "model": {"near_field": {"enabled": True, "options": {
            "max_time_s": 1.0, "oscillation_event_limit": 20}},
                  "far_field": {"enabled": False}},
        "criteria": [{"id": "dt2", "type": "isotherm_extent", "threshold_delta_T_C": 2}],
        "workspace": {"root": "workspace", "shared_provider_cache": True},
        "outputs": {"save": {"spatial_fields": "selected"}},
    }
    normalized = normalize_config(raw)
    return LoadedConfig(tmp_path / "template.yaml", normalized, _digest(normalized))


def test_pin_and_compare_two_real_model_field_variants_without_provider_refetch(tmp_path):
    base = _template(tmp_path)
    from plume.design import snapshot as snapshot_module
    with patch.object(snapshot_module, "load_provider", wraps=snapshot_module.load_provider) as io:
        pin = pin_snapshot(base)
        assert io.call_count == 5
        assert pin.at_utc == "2025-01-01T00:00:00Z"
        assert pin.source_scalars["flow_m3h"] == 540
        a = evaluate_design(base.normalized, pin, thermodynamics=LinearThermo(),
                            section_resolution=(41, 31), plan_resolution=(41, 31))
        b_cfg = candidate_config(base.normalized, depth_m=12, diameter_m=0.50,
                                 angle_deg=25, azimuth_deg=90, flow_m3h=540, delta_T_C=10)
        b = evaluate_design(b_cfg, pin, thermodynamics=LinearThermo(),
                            section_resolution=(41, 31), plan_resolution=(41, 31))
        assert io.call_count == 5  # this is the key DESIGN-1 provider discriminator
    assert a.config_sha256 != b.config_sha256
    assert a.metrics["final_bulk_dilution"] != b.metrics["final_bulk_dilution"]
    assert a.section.plane == "section" and b.plan.plane == "plan"
    assert a.section.values.delta_temperature_C.shape == (31, 41)
    assert a.metrics["model_status"].startswith("UNVALIDATED")
    assert a.metrics["criterion_status"].startswith("NOT_ASSESSED")
    assert a.record()["snapshot_sha256"] == b.record()["snapshot_sha256"]
    assert np.all(np.isfinite(a.plan.values.delta_temperature_C))


def test_stale_ambient_or_site_requires_repin(tmp_path):
    cfg = _template(tmp_path)
    pin = pin_snapshot(cfg)
    modified = copy.deepcopy(cfg.normalized)
    modified["forcing"]["ambient"]["current_profile"]["u_east_mps"] = .25
    with pytest.raises(ProviderDataError, match="repin"):
        evaluate_design(modified, pin, thermodynamics=LinearThermo())
    modified = copy.deepcopy(cfg.normalized)
    modified["site"]["latitude_deg"] = 61
    with pytest.raises(ProviderDataError, match="repin"):
        evaluate_design(modified, pin, thermodynamics=LinearThermo())


def test_snapshot_roundtrip_and_corruption_fails(tmp_path):
    pin = pin_snapshot(_template(tmp_path))
    assert PinnedSnapshot.from_record(json.loads(json.dumps(pin.as_record()))) == pin
    modified = pin.as_record()
    modified["temperature_profile_C"][0][1] = 50
    with pytest.raises(ProviderDataError, match="identity"):
        PinnedSnapshot.from_record(modified)
    fresh = pin_snapshot(_template(tmp_path))
    fresh.source_scalars["delta_T_C"] = 99  # nested dict mutation of frozen outer object
    with pytest.raises(ProviderDataError, match="changed since pin"):
        evaluate_design(_template(tmp_path).normalized, fresh, thermodynamics=LinearThermo())


def test_csv_depth_profile_pins_with_digest_and_fails_on_unordered_rows(tmp_path):
    path = tmp_path / "water.csv"
    path.write_text("depth_m,value\n0,13\n10,11\n25,9\n", encoding="utf-8")
    spec = normalize_provider_spec({"provider": "csv_depth_profile", "path": "water.csv"},
                                   context="ambient.temp")
    result = load_provider(spec, context=ProviderContext(config_dir=tmp_path))
    assert result.data_kind == "depth_profile"
    assert result.provenance.input_sha256
    cfg = _template(tmp_path)
    normalized = copy.deepcopy(cfg.normalized)
    normalized["forcing"]["ambient"]["temperature_profile_C"] = spec
    loaded = LoadedConfig(cfg.source_path, normalized, _digest(normalized))
    pinned = pin_snapshot(loaded)
    assert pinned.providers["forcing.ambient.temperature_profile_C"]["input_sha256"]
    path.write_text("depth_m,value\n0,13\n25,9\n10,11\n", encoding="utf-8")
    with pytest.raises(ProviderDataError, match="non-increasing"):
        pin_snapshot(loaded)


def test_save_reopen_and_lock_revisions_without_overwriting(tmp_path):
    store = ProjectStore(tmp_path / "ignored-workspace")
    created = store.create(_template(tmp_path), project_id="client-a", name="Client A")
    assert created.locked_revision_id is None
    assert store.list_projects() == ("client-a",)
    pin = pin_snapshot(created.config)
    first = evaluate_design(created.config.normalized, pin, thermodynamics=LinearThermo(),
                            section_resolution=(41, 31), plan_resolution=(41, 31))
    when = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    first_lock = store.save_revision(created, first, now=when)
    assert first_lock.is_locked
    assert (first_lock.project_dir / "revisions" / first_lock.locked_revision_id / "evaluation.json").exists()
    assert store.open("client-a").config.sha256 == first_lock.config.sha256
    assert store.load_locked_snapshot(first_lock).snapshot_sha256 == pin.snapshot_sha256
    with pytest.raises(WorkspaceError, match="changed since"):
        store.save_revision(created, first, now=when)
    second_cfg = candidate_config(first_lock.config.normalized, depth_m=12, diameter_m=.50,
                                  angle_deg=15, azimuth_deg=90, flow_m3h=540, delta_T_C=10)
    second = evaluate_design(second_cfg, pin, thermodynamics=LinearThermo(),
                             section_resolution=(41, 31), plan_resolution=(41, 31))
    second_lock = store.save_revision(first_lock, second, now=when)
    assert second_lock.locked_revision_id != first_lock.locked_revision_id
    assert len(list((second_lock.project_dir / "revisions").iterdir())) == 2
    assert second_lock.config.normalized["outfall"]["diameter_m"] == .50
    assert second_lock.config.source_dir == second_lock.project_dir
    assert (second_lock.project_dir / "project.yaml").is_file()
    import yaml
    from plume.design import export_snapshot_yaml
    locked_snapshot = store.load_locked_snapshot(second_lock)
    exported = yaml.safe_load(export_snapshot_yaml(second_lock, locked_snapshot))
    assert exported["outfall"]["diameter_m"] == .50
    assert exported["forcing"]["ambient"]["temperature_profile_C"]["provider"] == "inline_profile"
    wrong_timestamp = pin_snapshot(second_lock.config, at_utc="2025-01-01T01:00:00Z")
    with pytest.raises(WorkspaceError, match="locked revision"):
        export_snapshot_yaml(second_lock, wrong_timestamp)


def test_exact_csv_scalar_time_pin_and_out_of_range_fail(tmp_path):
    file = tmp_path / "flow.csv"
    file.write_text("time,value\n2025-01-01T00:00:00Z,540\n2025-01-01T01:00:00Z,600\n")
    raw = copy.deepcopy(_template(tmp_path).normalized)
    raw["forcing"]["source"]["flow_m3h"] = {
        "provider": "csv", "path": "flow.csv", "time_column": "time", "value_column": "value"}
    loaded = LoadedConfig(tmp_path / "template.yaml", normalize_config(raw), _digest(normalize_config(raw)))
    pin = pin_snapshot(loaded, at_utc="2025-01-01T01:00:00Z")
    assert pin.source_scalars["flow_m3h"] == 600
    with pytest.raises(ProviderDataError, match="no exact sample"):
        pin_snapshot(loaded, at_utc="2025-01-01T02:00:00Z")
