from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.reference_harness.manifest import ManifestError, load_manifest, validate_manifest


class ManifestTests(unittest.TestCase):
    def _valid(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "case_id": "P-EXAMPLE-SSMC",
            "purpose": "build control",
            "role": "software_regression",
            "reference": {
                "kind": "checked_in_distribution",
                "identity": "tree:d1d40f74ffc6538f3e1f3ea4ca9dd02d8b530856",
            },
            "inputs": [],
            "raw_outputs": [
                {
                    "path": "References/PLUMES2.0-main/Example_project/ModelResults_TxtOutputs.dat",
                    "git_blob_sha": "765fff0e5d55d1ce91bfcb139e48843b148eed84",
                    "size_bytes": 6660,
                }
            ],
            "normalization": {
                "parser": "plumes_modelresults_v1",
                "coordinates": "surface_zero_z_positive_up",
            },
        }

    def test_valid_manifest_round_trips(self) -> None:
        manifest = self._valid()
        self.assertIs(validate_manifest(manifest), manifest)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(load_manifest(path), manifest)

    def test_hold_back_and_calibration_are_explicit_roles(self) -> None:
        manifest = self._valid()
        manifest["role"] = "hold_back"
        self.assertEqual(validate_manifest(manifest)["role"], "hold_back")
        manifest["role"] = "calibration"
        self.assertEqual(validate_manifest(manifest)["role"], "calibration")

    def test_rejects_parent_escape(self) -> None:
        manifest = self._valid()
        manifest["raw_outputs"][0]["path"] = "../References/output.dat"  # type: ignore[index]
        with self.assertRaisesRegex(ManifestError, "repository-relative"):
            validate_manifest(manifest)

    def test_rejects_implicit_coordinate_convention(self) -> None:
        manifest = self._valid()
        manifest["normalization"]["coordinates"] = "whatever-the-source-says"  # type: ignore[index]
        with self.assertRaisesRegex(ManifestError, "surface_zero_z_positive_up"):
            validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
