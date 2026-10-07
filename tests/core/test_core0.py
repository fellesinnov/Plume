from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

from plume.config import load_config
from plume.errors import (
    ConfigError,
    ProviderDataError,
    UnsupportedOutletError,
    UnsupportedProviderError,
    UnsupportedSchemaVersionError,
    WorkspaceError,
)
from plume.providers import ProviderContext, load_provider
from plume.workspace import prepare_run, resolve_workspace_root

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "configs" / "example.yaml"


class ConfigTests(unittest.TestCase):
    def test_example_loads_and_normalizes_headlessly(self) -> None:
        loaded = load_config(EXAMPLE)
        self.assertEqual(loaded.normalized["schema_version"], 1)
        self.assertEqual(loaded.project_id, "demo_thermal_outfall")
        self.assertEqual(loaded.normalized["outfall"]["type"], "single_round_port")
        self.assertEqual(loaded.normalized["forcing"]["clock"]["start"], "2025-01-01T00:00:00Z")
        self.assertEqual(loaded.normalized["workspace"]["root"], "../workspace")
        self.assertEqual(resolve_workspace_root(loaded), ROOT / "workspace")
        self.assertEqual(len(loaded.sha256), 64)

    def test_json_is_supported_by_same_normalizer(self) -> None:
        raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
        raw["forcing"]["clock"]["start"] = "2025-01-01T00:00:00Z"
        raw["forcing"]["clock"]["end"] = "2025-01-07T00:00:00Z"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            loaded = load_config(path)
        self.assertEqual(loaded.normalized["site"]["latitude_deg"], 60.0)

    def test_unsupported_schema_version_is_explicit(self) -> None:
        raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
        raw["schema_version"] = 2
        with self.assertRaisesRegex(UnsupportedSchemaVersionError, "unsupported schema_version"):
            self._load_temp(raw)

    def test_unsupported_outlet_is_explicit_discriminator(self) -> None:
        raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
        raw["outfall"]["type"] = "multiport_diffuser"
        with self.assertRaisesRegex(UnsupportedOutletError, "multiport_diffuser"):
            self._load_temp(raw)

    def test_unsupported_provider_is_explicit_discriminator(self) -> None:
        raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
        raw["forcing"]["source"]["flow_m3h"]["provider"] = "constant_typo"
        with self.assertRaisesRegex(UnsupportedProviderError, "constant_typo"):
            self._load_temp(raw)

    def test_unknown_top_level_key_fails(self) -> None:
        raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
        raw["streamlit_state"] = {}
        with self.assertRaisesRegex(ConfigError, "unsupported field"):
            self._load_temp(raw)

    def test_inline_profile_is_sorted_and_duplicate_depth_fails(self) -> None:
        raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
        levels = raw["forcing"]["ambient"]["temperature_profile_C"]["levels"]
        raw["forcing"]["ambient"]["temperature_profile_C"]["levels"] = list(reversed(levels))
        loaded = self._load_temp(raw)
        depths = [
            row["depth_m"]
            for row in loaded.normalized["forcing"]["ambient"]["temperature_profile_C"]["levels"]
        ]
        self.assertEqual(depths, [0.0, 10.0, 20.0])

        raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
        raw["forcing"]["ambient"]["temperature_profile_C"]["levels"].append(
            {"depth_m": 10.0, "value": 8.1}
        )
        with self.assertRaisesRegex(ConfigError, "duplicate depth_m"):
            self._load_temp(raw)

    def _load_temp(self, raw: dict) -> object:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "config.yaml"
        path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        return load_config(path)


class ProviderTests(unittest.TestCase):
    def test_csv_resolves_relative_to_config_and_records_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plant = root / "plant"
            plant.mkdir()
            csv_path = plant / "flow.csv"
            csv_bytes = (
                b"timestamp,flow_m3h\n"
                b"2025-01-01T00:00:00Z,1000\n"
                b"2025-01-01T01:00:00+00:00,1100.5\n"
            )
            csv_path.write_bytes(csv_bytes)
            spec = {
                "provider": "csv",
                "path": "plant/flow.csv",
                "time_column": "timestamp",
                "value_column": "flow_m3h",
            }
            result = load_provider(spec, context=ProviderContext(config_dir=root))
            self.assertEqual(result.data_kind, "scalar_time_series")
            self.assertEqual(result.records[1]["value"], 1100.5)
            self.assertEqual(result.records[1]["time"], "2025-01-01T01:00:00Z")
            self.assertEqual(result.provenance.input_sha256, hashlib.sha256(csv_bytes).hexdigest())
            self.assertEqual(Path(result.provenance.source), csv_path)

    def test_csv_rejects_ambiguous_or_non_monotonic_time(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "bad.csv"
            path.write_text(
                "timestamp,value\n2025-01-01T01:00:00Z,1\n2025-01-01T00:00:00Z,2\n",
                encoding="utf-8",
            )
            spec = {
                "provider": "csv",
                "path": "bad.csv",
                "time_column": "timestamp",
                "value_column": "value",
            }
            with self.assertRaisesRegex(ProviderDataError, "strictly increasing"):
                load_provider(spec, context=ProviderContext(config_dir=root))


class WorkspaceTests(unittest.TestCase):
    def test_prepare_example_writes_normalized_config_and_manifest(self) -> None:
        loaded = load_config(EXAMPLE)
        with tempfile.TemporaryDirectory() as temp:
            prepared = prepare_run(
                loaded,
                workspace_override=temp,
                run_id="core0-smoke",
                git_sha="0123456789abcdef",
                now=lambda: datetime(2026, 10, 7, 11, 30, tzinfo=timezone.utc),
            )
            self.assertTrue(prepared.normalized_config_path.is_file())
            self.assertTrue(prepared.manifest_path.is_file())
            self.assertEqual(
                prepared.run_dir,
                Path(temp) / "projects" / "demo_thermal_outfall" / "runs" / "core0-smoke",
            )
            manifest = json.loads(prepared.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["stage"], "prepared")
            self.assertEqual(manifest["config"]["normalized_sha256"], loaded.sha256)
            self.assertEqual(manifest["software"]["git_sha"], "0123456789abcdef")
            self.assertEqual(manifest["coordinates"]["frame"], "ENU")
            self.assertEqual(
                manifest["providers"]["forcing.ambient.current_profile"]["data_kind"],
                "vector_constant",
            )
            self.assertEqual(
                manifest["providers"]["forcing.ambient.temperature_profile_C"]["record_count"],
                3,
            )
            self.assertFalse(manifest["warnings"])

    def test_existing_run_is_never_silently_overwritten(self) -> None:
        loaded = load_config(EXAMPLE)
        with tempfile.TemporaryDirectory() as temp:
            prepare_run(loaded, workspace_override=temp, run_id="same", git_sha="test")
            with self.assertRaisesRegex(WorkspaceError, "already exists"):
                prepare_run(loaded, workspace_override=temp, run_id="same", git_sha="test")

    def test_provider_failure_does_not_leave_partial_run_directory(self) -> None:
        raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
        raw["forcing"]["source"]["flow_m3h"] = {
            "provider": "csv",
            "path": "missing/flow.csv",
            "time_column": "timestamp",
            "value_column": "flow_m3h",
        }
        with tempfile.TemporaryDirectory() as config_temp, tempfile.TemporaryDirectory() as workspace_temp:
            path = Path(config_temp) / "config.yaml"
            path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
            loaded = load_config(path)
            with self.assertRaisesRegex(ProviderDataError, "does not exist"):
                prepare_run(
                    loaded,
                    workspace_override=workspace_temp,
                    run_id="bad-provider",
                    git_sha="test",
                )
            run_dir = (
                Path(workspace_temp)
                / "projects"
                / loaded.project_id
                / "runs"
                / "bad-provider"
            )
            self.assertFalse(run_dir.exists())

    def test_cli_prepare_is_headless(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "plume",
                    "prepare",
                    str(EXAMPLE),
                    "--workspace",
                    temp,
                    "--run-id",
                    "cli-smoke",
                    "--git-sha",
                    "test-sha",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            run_dir = Path(completed.stdout.strip())
            self.assertTrue((run_dir / "manifest.json").is_file())
            self.assertTrue((run_dir / "config.normalized.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
