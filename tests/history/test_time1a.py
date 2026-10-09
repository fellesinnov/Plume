"""TIME-1A historical contracts, gaps, cache and source-restoration regressions.

All data here are manufactured deterministic input *fixtures*, not ocean
observations or physical validation. The physics kernel is not run in TIME-1A.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from plume.config import LoadedConfig
from plume.design.snapshot import PinnedSnapshot, _digest
from plume.errors import ProviderDataError
from plume.history import acquire_history
from plume.providers import ProviderContext, load_provider, normalize_provider_spec


TIMES = [f"2025-01-01T0{i}:00:00Z" for i in range(3)]


def _cfg(tmp_path: Path) -> LoadedConfig:
    (tmp_path / "T.csv").write_text(
        "time,depth_m,value\n"
        "2025-01-01T00:00:00Z,0,12\n2025-01-01T00:00:00Z,10,11\n2025-01-01T00:00:00Z,20,9\n"
        "2025-01-01T02:00:00Z,0,13\n2025-01-01T02:00:00Z,10,12\n2025-01-01T02:00:00Z,20,10\n")
    (tmp_path / "S.csv").write_text(
        "time,depth_m,value\n"
        "2025-01-01T00:00:00+00:00,0,34\n2025-01-01T00:00:00Z,20,35\n"
        "2025-01-01T02:00:00Z,0,34.2\n2025-01-01T02:00:00Z,20,35.1\n")
    (tmp_path / "uv.csv").write_text(
        "time,depth_m,u_east_mps,v_north_mps\n"
        "2025-01-01T00:00:00Z,0,0.2,0.0\n2025-01-01T00:00:00Z,20,0.1,0.1\n"
        "2025-01-01T02:00:00Z,0,0.3,0.0\n2025-01-01T02:00:00Z,20,0.15,0.05\n")
    (tmp_path / "flow.csv").write_text(
        "time,value\n2025-01-01T00:00:00Z,450\n2025-01-01T02:00:00Z,550\n")
    source = {"flow_m3h": {"provider": "csv", "path": "flow.csv", "time_column": "time", "value_column": "value"},
              "delta_T_C": {"provider": "constant", "value": 10.0}}
    ambient = {
        "temperature_profile_C": {"provider": "csv_time_depth_profile", "path": "T.csv"},
        "salinity_profile_psu": {"provider": "csv_time_depth_profile", "path": "S.csv"},
        "current_profile": {"provider": "csv_time_vector_profile", "path": "uv.csv"},
    }
    for group in (source, ambient):
        for k, spec in list(group.items()):
            group[k] = normalize_provider_spec(spec, context=k)
    raw = {
        "schema_version": 1, "project": {"id": "siteA", "name": "A"},
        "site": {"latitude_deg": 60.0, "longitude_deg": 5.0, "water_depth_m": 20.0},
        "outfall": {"type": "single_round_port", "diameter_m": 0.5,
                    "discharge_depth_below_surface_m": 12.0, "azimuth_deg": 90.0,
                    "vertical_angle_deg": 0.0},
        "forcing": {"clock": {"start": TIMES[0], "end": "2025-01-01T03:00:00Z", "step": "PT1H"},
                    "source": source, "ambient": ambient},
        "model": {"near_field": {"enabled": True}, "far_field": {"enabled": False}},
        "criteria": [], "workspace": {"root": "workspace", "shared_provider_cache": True},
        "outputs": {},
    }
    return LoadedConfig(tmp_path / "config.yaml", raw, _digest(raw))


def test_history_time_depth_current_and_original_plant_series_are_selected_exactly(tmp_path):
    cfg = _cfg(tmp_path)
    from plume.history import history as module
    with patch.object(module, "load_provider", wraps=module.load_provider) as provider:
        first = acquire_history(cfg, workspace_override=tmp_path / "workspace")
        assert provider.call_count == 5
        assert first.clock_times == tuple(TIMES)
        assert first.available_times == (TIMES[0], TIMES[2])
        assert first.missing_by_time[TIMES[1]] == (
            "ambient.current_profile", "ambient.salinity_profile_psu",
            "ambient.temperature_profile_C", "source.flow_m3h")
        a = first.snapshot_at(cfg, TIMES[0])
        b = first.snapshot_at(cfg, TIMES[2])
        assert provider.call_count == 5  # cached snapshot selection performs NO I/O
        assert a.current_profile_east_north_mps == ((0, 0.2, 0.0), (20, 0.1, 0.1))
        assert b.current_profile_east_north_mps == ((0, 0.3, 0.0), (20, 0.15, 0.05))
        assert a.current_east_north_mps == (0.2, 0.0)  # surface summary only
        assert a.temperature_profile_C[0] == (0, 12)
        assert b.temperature_profile_C[0] == (0, 13)
        assert a.source_scalars["flow_m3h"] == 450
        assert b.source_scalars["flow_m3h"] == 550
        assert a.source_specs["flow_m3h"]["provider"] == "csv"  # never frozen to 450
        assert b.source_specs["flow_m3h"]["provider"] == "csv"
        assert first.request_sha256 == _digest(first.request)
        assert a.snapshot_sha256 != b.snapshot_sha256
        assert PinnedSnapshot.from_record(json.loads(json.dumps(a.as_record()))) == a
        with pytest.raises(ProviderDataError, match="missing forcing"):
            first.snapshot_at(cfg, TIMES[1])
        with pytest.raises(ProviderDataError, match="outside selected clock"):
            first.snapshot_at(cfg, "2025-01-01T03:00:00Z")
        same = acquire_history(cfg, workspace_override=tmp_path / "workspace")
        assert same.cache_hit
        assert same.data_sha256 == first.data_sha256
        assert provider.call_count == 5  # same request from disk, no provider reload
        assert same.snapshot_at(cfg, TIMES[2]).source_scalars == b.source_scalars
    assert len(tuple(first.iter_available(cfg))) == 2


def test_geometry_changes_reuse_history_but_design_locked_constant_source_does_not(tmp_path):
    cfg = _cfg(tmp_path)
    first = acquire_history(cfg, workspace_override=tmp_path / "workspace")
    altered = copy.deepcopy(cfg.normalized)
    altered["outfall"]["diameter_m"] = 0.8
    geometry = LoadedConfig(cfg.source_path, altered, _digest(altered))
    assert first.snapshot_at(geometry, TIMES[0]).source_scalars["flow_m3h"] == 450
    altered["forcing"]["source"]["flow_m3h"] = {"provider": "constant", "value": 450.0}
    locked = LoadedConfig(cfg.source_path, altered, _digest(altered))
    with pytest.raises(ProviderDataError, match="source changed.*do not reuse locked design constants"):
        first.snapshot_at(locked, TIMES[0])


def test_local_cache_changes_when_historical_source_csv_bytes_change(tmp_path):
    cfg = _cfg(tmp_path)
    first = acquire_history(cfg, workspace_override=tmp_path / "workspace")
    flow = tmp_path / "flow.csv"
    flow.write_text(flow.read_text().replace("550", "600"))
    second = acquire_history(cfg, workspace_override=tmp_path / "workspace")
    assert not second.cache_hit
    assert first.request_sha256 != second.request_sha256
    assert first.cache_path != second.cache_path
    assert first.snapshot_at(cfg, TIMES[2]).source_scalars["flow_m3h"] == 550
    assert second.snapshot_at(cfg, TIMES[2]).source_scalars["flow_m3h"] == 600


def test_corrupted_history_cache_or_mutated_pinned_state_rejected(tmp_path):
    cfg = _cfg(tmp_path)
    original = acquire_history(cfg, workspace_override=tmp_path / "workspace")
    raw = json.loads(original.cache_path.read_text())
    raw["series"]["source.flow_m3h"]["records_by_time"][TIMES[0]][0]["value"] = 999
    original.cache_path.write_text(json.dumps(raw))
    with pytest.raises(ProviderDataError, match="digest mismatch"):
        acquire_history(cfg, workspace_override=tmp_path / "workspace")
    pinned = original.snapshot_at(cfg, TIMES[0])
    pinned.current_profile_east_north_mps  # frozen tuple
    pinned.source_scalars["flow_m3h"] = 888  # mutable nested dictionary protection
    with pytest.raises(ProviderDataError, match="changed since pin"):
        pinned.verify_identity()


def test_invalid_history_csv_fails_loudly_without_time_or_depth_guesswork(tmp_path):
    cfg = _cfg(tmp_path)
    file = tmp_path / "T.csv"
    file.write_text(file.read_text().replace("2025-01-01T00:00:00Z,10,11", "2025-01-01T00:00:00Z,0,11"))
    with pytest.raises(ProviderDataError, match="strictly ordered"):
        acquire_history(cfg, workspace_override=tmp_path / "workspace")
    cfg = _cfg(tmp_path)
    file.write_text(file.read_text().replace("2025-01-01T00:00:00Z,10,11", "2025-01-01T00:00:00Z,10,nan"))
    with pytest.raises(ProviderDataError, match="finite"):
        acquire_history(cfg, workspace_override=tmp_path / "workspace")
    cfg = _cfg(tmp_path)
    file.write_text(file.read_text().replace("2025-01-01T00:00:00Z", "2025-01-01T00:00:00", 1))
    with pytest.raises(ProviderDataError, match="invalid time"):
        acquire_history(cfg, workspace_override=tmp_path / "workspace")
    cfg = _cfg(tmp_path)
    file.write_text(file.read_text().replace("2025-01-01T00:00:00Z,20,9", "2025-01-01T00:00:00Z,18,9"))
    with pytest.raises(ProviderDataError, match="cover 0 and water depth"):
        acquire_history(cfg, workspace_override=tmp_path / "workspace")


def test_rejects_partial_current_water_column_and_negative_salinity(tmp_path):
    cfg = _cfg(tmp_path)
    uv = tmp_path / "uv.csv"
    uv.write_text(uv.read_text().replace("2025-01-01T00:00:00Z,20,0.1,0.1", "2025-01-01T00:00:00Z,19,0.1,0.1"))
    with pytest.raises(ProviderDataError, match="depth-vector profile must cover"):
        acquire_history(cfg, workspace_override=tmp_path / "workspace")
    cfg = _cfg(tmp_path)
    salt = tmp_path / "S.csv"
    salt.write_text(salt.read_text().replace("2025-01-01T02:00:00Z,20,35.1", "2025-01-01T02:00:00Z,20,-1"))
    with pytest.raises(ProviderDataError, match="Practical Salinity"):
        acquire_history(cfg, workspace_override=tmp_path / "workspace")


def test_local_private_cache_and_request_identity_include_site(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.normalized["workspace"]["shared_provider_cache"] = False
    local = acquire_history(cfg, workspace_override=tmp_path / "cache-root")
    assert "projects/siteA/_cache/history" in local.cache_path.as_posix()
    site = copy.deepcopy(cfg.normalized)
    site["site"]["latitude_deg"] = 61.0
    fresh = LoadedConfig(cfg.source_path, site, _digest(site))
    other = acquire_history(fresh, workspace_override=tmp_path / "cache-root")
    assert other.request_sha256 != local.request_sha256
    with pytest.raises(ProviderDataError, match="site changed"):
        local.snapshot_at(fresh, TIMES[0])


def test_source_time_grid_has_explicit_missing_provenance_and_no_interpolation(tmp_path):
    cfg = _cfg(tmp_path)
    h = acquire_history(cfg, workspace_override=tmp_path / "workspace")
    assert h.missing_by_time == {TIMES[1]: (
        "ambient.current_profile", "ambient.salinity_profile_psu",
        "ambient.temperature_profile_C", "source.flow_m3h")}
    assert h.available_times == (TIMES[0], TIMES[2])
    for name, item in h.series.items():
        assert item["provenance"]["provider"]
        if item["provenance"]["source"].endswith(".csv"):
            assert len(item["provenance"]["input_sha256"]) == 64


def test_static_ambient_and_constant_current_reuse_original_pin_contract(tmp_path):
    cfg = _cfg(tmp_path)
    raw = copy.deepcopy(cfg.normalized)
    for name, levels in (
        ("temperature_profile_C", [(0, 11), (20, 9)]),
        ("salinity_profile_psu", [(0, 34), (20, 35)]),
    ):
        raw["forcing"]["ambient"][name] = {
            "provider": "inline_profile",
            "levels": [{"depth_m": z, "value": v} for z, v in levels],
        }
    raw["forcing"]["ambient"]["current_profile"] = {
        "provider": "constant_vector", "u_east_mps": 0.2, "v_north_mps": 0.1,
    }
    loaded = LoadedConfig(cfg.source_path, raw, _digest(raw))
    history = acquire_history(loaded, workspace_override=tmp_path / "static-cache")
    a = history.snapshot_at(loaded, TIMES[0])
    b = history.snapshot_at(loaded, TIMES[2])
    assert a.current_profile_east_north_mps is None
    assert "current_profile_east_north_mps" not in a.as_record()
    assert a.temperature_profile_C == b.temperature_profile_C
    assert a.current_east_north_mps == (0.2, 0.1)
    assert a.source_scalars["flow_m3h"] == 450
    assert b.source_scalars["flow_m3h"] == 550


def test_utc_offsets_canonicalize_and_subsecond_depth_times_must_not_alias(tmp_path):
    cfg = _cfg(tmp_path)
    a = acquire_history(cfg, workspace_override=tmp_path / "cache")
    assert a.snapshot_at(cfg, "2025-01-01T02:00:00+00:00").at_utc == TIMES[2]
    raw = tmp_path / "T.csv"
    raw.write_text(raw.read_text().replace("2025-01-01T00:00:00Z,0,12",
                                            "2025-01-01T00:00:00.500Z,0,12"))
    with pytest.raises(ProviderDataError, match="invalid time/depth/value"):
        acquire_history(cfg, workspace_override=tmp_path / "cache")


def test_ambient_provider_shape_mismatch_fails_at_acquisition(tmp_path):
    cfg = _cfg(tmp_path)
    from plume.history import history as module
    original = module.load_provider
    def wrong_shape(spec, *, context):
        result = original(spec, context=context)
        if spec["provider"] == "csv_time_vector_profile":
            from plume.providers import ProviderResult
            return ProviderResult("scalar", ({"value": 3.0},), result.provenance)
        return result
    with patch.object(module, "load_provider", side_effect=wrong_shape):
        with pytest.raises(ProviderDataError, match="wrong historical provider shape"):
            acquire_history(cfg, workspace_override=tmp_path / "bad")


def test_full_year_uses_timestamp_index_and_does_not_materialize_solver_outputs(tmp_path):
    cfg = _cfg(tmp_path)
    raw = copy.deepcopy(cfg.normalized)
    raw["forcing"]["clock"] = {
        "start": "2025-01-01T00:00:00Z", "end": "2026-01-01T00:00:00Z", "step": "PT1H"}
    for key, val in (("temperature_profile_C", 10.0), ("salinity_profile_psu", 35.0)):
        raw["forcing"]["ambient"][key] = {
            "provider": "inline_profile", "levels": [
                {"depth_m": 0, "value": val}, {"depth_m": 20, "value": val-1 if key == "temperature_profile_C" else val},
            ]}
    raw["forcing"]["ambient"]["current_profile"] = {
        "provider": "constant_vector", "u_east_mps": 0.1, "v_north_mps": 0.0}
    raw["forcing"]["source"] = {"flow_m3h": {"provider": "constant", "value": 400},
                                 "delta_T_C": {"provider": "constant", "value": 8}}
    config = LoadedConfig(cfg.source_path, raw, _digest(raw))
    history = acquire_history(config, workspace_override=tmp_path / "large")
    assert len(history.clock_times) == 8760
    assert len(history.available_times) == 8760
    assert len(history.series) == 5
    assert all("records_by_time" not in s for s in history.series.values())
    selected = tuple(history.iter_available(config))
    assert len(selected) == 8760
    assert selected[-1].at_utc == "2025-12-31T23:00:00Z"
    assert all(s.current_profile_east_north_mps is None for s in selected)


def test_csv_changed_during_acquisition_must_not_be_cached_under_stale_request_sha(tmp_path):
    cfg = _cfg(tmp_path)
    from plume.history import history as module
    real_load = module.load_provider

    def race(spec, *, context):
        result = real_load(spec, context=context)
        if spec["provider"] == "csv_time_vector_profile":
            from plume.providers import ProviderProvenance, ProviderResult
            provenance = ProviderProvenance(
                result.provenance.provider, result.provenance.source,
                result.provenance.request, input_sha256="0" * 64,
                warnings=result.provenance.warnings)
            return ProviderResult(result.data_kind, result.records, provenance)
        return result

    with patch.object(module, "load_provider", side_effect=race):
        with pytest.raises(ProviderDataError, match="changed during historical acquisition"):
            acquire_history(cfg, workspace_override=tmp_path / "workspace")
    assert not list((tmp_path / "workspace").rglob("*.json"))


def test_project_paths_rebase_for_time_depth_csv_without_orphaning_files(tmp_path):
    """A named project must resolve historical input files after relocating config."""
    from plume.design.projects import ProjectStore
    cfg = _cfg(tmp_path)
    store = ProjectStore(tmp_path / "project-workspace")
    project = store.create(cfg, project_id="history-a", name="History A")
    assert project.config.project_id == "history-a"
    for group in ("source", "ambient"):
        for key, desc in project.config.normalized["forcing"][group].items():
            if desc["provider"] in {"csv", "csv_time_depth_profile", "csv_time_vector_profile"}:
                origin = cfg.normalized["forcing"][group][key]["path"]
                assert (project.config.source_dir / desc["path"]).resolve() == (tmp_path / origin).resolve()
    selected = acquire_history(project.config)
    assert selected.snapshot_at(project.config, TIMES[2]).source_scalars["flow_m3h"] == 550


def test_portable_project_export_rejects_external_historical_source_files(tmp_path):
    """Reject a portable config that would silently lose its input CSV dependency."""
    from plume.design.projects import DesignProject, ProjectStore, export_portable_yaml
    from plume.errors import WorkspaceError
    store = ProjectStore(tmp_path / "work")
    project = store.create(_cfg(tmp_path), project_id="history-a", name="History A")
    fake_locked = DesignProject(project.project_dir, project.config, "locked", project.config.sha256)
    with pytest.raises(WorkspaceError, match="companion CSV files"):
        export_portable_yaml(fake_locked)


def test_locked_snapshot_export_must_not_flatten_vertical_current_shear(tmp_path):
    """A one-hour YAML export cannot represent a historical depth-sheared current yet."""
    from plume.design.projects import DesignProject, ProjectStore, export_snapshot_yaml
    from plume.errors import WorkspaceError
    from plume.design.snapshot import PinnedSnapshot
    store = ProjectStore(tmp_path / "work")
    project = store.create(_cfg(tmp_path), project_id="history-a", name="History A")
    history = acquire_history(project.config)
    snapshot = history.snapshot_at(project.config, TIMES[0])
    assert snapshot.current_profile_east_north_mps is not None
    path = project.project_dir / "revisions" / "locked" / "snapshot.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(snapshot.as_record()), encoding="utf-8")
    fake_locked = DesignProject(project.project_dir, project.config, "locked", project.config.sha256)
    with pytest.raises(WorkspaceError, match="cannot export depth-varying current as constant_vector"):
        export_snapshot_yaml(fake_locked, PinnedSnapshot.from_record(snapshot.as_record()))



def test_year_selection_membership_indexes_are_derived_but_not_in_serialized_record(tmp_path):
    """Fast membership indices avoid O(year**2) scans but are not persisted."""
    cfg = _cfg(tmp_path)
    first = acquire_history(cfg, workspace_override=tmp_path / "cache")
    assert isinstance(first._clock_index, frozenset)
    assert isinstance(first._available_index, frozenset)
    assert len(first._clock_index) == len(first.clock_times) == 3
    assert first._available_index == frozenset(first.available_times)
    assert "_clock_index" not in first.as_record()
    assert "_available_index" not in first.as_record()
    cached = acquire_history(cfg, workspace_override=tmp_path / "cache")
    assert cached.cache_hit
    assert cached._available_index == first._available_index
    assert cached.snapshot_at(cfg, TIMES[2]).snapshot_sha256 == first.snapshot_at(cfg, TIMES[2]).snapshot_sha256



def test_scalar_plant_sample_fractional_second_must_not_alias_clock_hour(tmp_path):
    """An actual 00:00:00.5 measurement may not masquerade as 00:00:00."""
    cfg = _cfg(tmp_path)
    plant = tmp_path / "flow.csv"
    plant.write_text(plant.read_text().replace("2025-01-01T00:00:00Z,450",
                                                 "2025-01-01T00:00:00.500Z,450"))
    history = acquire_history(cfg, workspace_override=tmp_path / "workspace")
    assert history.available_times == (TIMES[2],)
    assert "source.flow_m3h" in history.missing_by_time[TIMES[0]]
    assert history.snapshot_at(cfg, TIMES[2]).source_scalars["flow_m3h"] == 550


def test_fractional_clock_start_or_end_is_never_silently_truncated(tmp_path):
    from plume.history.history import _clock_times
    clock = {"start": "2025-01-01T00:00:00.500Z", "end": "2025-01-01T03:00:00Z", "step": "PT1H"}
    with pytest.raises(ProviderDataError, match="whole-second UTC clock boundaries"):
        _clock_times(clock)
    clock = {"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T03:00:00.500Z", "step": "PT1H"}
    with pytest.raises(ProviderDataError, match="whole-second UTC clock boundaries"):
        _clock_times(clock)



def test_schema_rejects_fractional_clock_boundaries_before_canonicalization(tmp_path):
    """Config normalization may not hide a half-second shift in model forcing."""
    from plume.config import normalize_config
    from plume.errors import ConfigError
    original = _cfg(tmp_path).normalized
    for boundary in ("start", "end"):
        raw = copy.deepcopy(original)
        raw["forcing"]["clock"][boundary] = (
            "2025-01-01T00:00:00.500Z" if boundary == "start" else
            "2025-01-01T03:00:00.500Z")
        with pytest.raises(ConfigError, match="whole-second UTC timestamps"):
            normalize_config(raw)
