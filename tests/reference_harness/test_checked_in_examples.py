from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest
import warnings

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.reference_harness.compare_examples import comparison_summary
from tools.reference_harness.manifest import load_manifest
from tools.reference_harness.plumes_dat import parse_modelresults
from tools.reference_harness.worktree_identity import (
    ReferenceIdentityError, check_pinned_worktree, git_blob_sha,
)

REFERENCE_ROOT = ROOT / "References"
CASES = ROOT / "tests" / "reference" / "cases"
EXPECTED = ROOT / "tests" / "reference" / "expected"
LOCK = ROOT / "tests" / "reference" / "reference-lock.json"


def _git_blob_sha(path: Path) -> str:
    return git_blob_sha(path.read_bytes())


@unittest.skipUnless(REFERENCE_ROOT.exists(), "full checked-in References tree not mounted")
class CheckedInReferenceTests(unittest.TestCase):
    def test_case_manifests_pin_committed_git_input_and_output_bytes(self) -> None:
        converted = []
        for manifest_path in sorted(CASES.glob("P-EXAMPLE-*.json")):
            manifest = load_manifest(manifest_path)
            for artifact in [*manifest.get("inputs", []), *manifest["raw_outputs"]]:
                path = ROOT / artifact["path"]
                self.assertTrue(path.is_file(), artifact["path"])
                # Git's original blob is authoritative; older Windows clones
                # can retain CRLF working copies despite current .gitattributes.
                # Do not modify or claim those working copies are byte-exact.
                tolerate_crlf = (sys.platform == "win32"
                                 and path.suffix.lower() in {".prj", ".csv", ".dat"})
                try:
                    exact_worktree = check_pinned_worktree(
                        path.read_bytes(),
                        size_bytes=artifact["size_bytes"],
                        git_sha=artifact["git_blob_sha"],
                        tolerate_windows_crlf=tolerate_crlf,
                    )
                except ReferenceIdentityError as exc:
                    self.fail(f"{artifact['path']}: {exc}")
                if not exact_worktree:
                    converted.append(artifact["path"])
        if converted:
            warnings.warn(
                f"{len(converted)} reference text worktree file(s) have Windows "
                "CRLF conversion: the original pinned Git SHA and byte size "
                "match after READ-ONLY in-memory reversal, but the local "
                "working copies are NOT byte-identical. Use a clean Git "
                f"checkout for raw-byte experiments. First: {converted[0]}",
                RuntimeWarning,
                stacklevel=1,
            )

    def test_reference_lock_pins_the_actual_executable_bytes(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for distribution in lock["checked_in_distributions"]:
            executable = distribution["executable"]
            path = ROOT / executable["path"]
            self.assertEqual(path.stat().st_size, executable["size_bytes"], executable["path"])
            self.assertEqual(_git_blob_sha(path), executable["git_blob_sha"], executable["path"])
            if executable["sha256"] is not None:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(digest, executable["sha256"], executable["path"])

    def test_shipped_example_comparison_reproduces_the_derived_golden(self) -> None:
        left_manifest = load_manifest(CASES / "P-EXAMPLE-SSMC.json")
        right_manifest = load_manifest(CASES / "P-EXAMPLE-EPA-2025-12-22.json")
        left = parse_modelresults(ROOT / left_manifest["raw_outputs"][0]["path"])
        right = parse_modelresults(ROOT / right_manifest["raw_outputs"][0]["path"])
        actual = comparison_summary(left, right)
        expected = json.loads(
            (EXPECTED / "P-EXAMPLE-build-comparison.json").read_text(encoding="utf-8")
        )
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
