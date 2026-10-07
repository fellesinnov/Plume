"""Small stdlib-only manifest contract for derived reference cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ALLOWED_ROLES = {"software_regression", "mechanism", "calibration", "hold_back"}
_ALLOWED_REFERENCE_KINDS = {"checked_in_distribution", "external_repository", "literature"}


class ManifestError(ValueError):
    """Raised when a reference-case manifest violates the REF-1 contract."""


def _require(mapping: dict[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise ManifestError(f"{where}: missing required key {key!r}")
    return mapping[key]


def _require_nonempty_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{where}: expected a non-empty string")
    return value


def _validate_artifact(artifact: Any, where: str) -> None:
    if not isinstance(artifact, dict):
        raise ManifestError(f"{where}: expected an object")
    path = _require_nonempty_string(_require(artifact, "path", where), f"{where}.path")
    if Path(path).is_absolute() or ".." in Path(path).parts:
        raise ManifestError(f"{where}.path: repository-relative path required")
    git_blob_sha = _require_nonempty_string(
        _require(artifact, "git_blob_sha", where), f"{where}.git_blob_sha"
    )
    if len(git_blob_sha) != 40 or any(c not in "0123456789abcdef" for c in git_blob_sha):
        raise ManifestError(f"{where}.git_blob_sha: expected lowercase 40-char Git SHA-1")
    if "size_bytes" in artifact:
        size = artifact["size_bytes"]
        if not isinstance(size, int) or size < 0:
            raise ManifestError(f"{where}.size_bytes: expected non-negative integer")
    if "sha256" in artifact and artifact["sha256"] is not None:
        digest = artifact["sha256"]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ManifestError(f"{where}.sha256: expected lowercase 64-char SHA-256")


def validate_manifest(manifest: Any) -> dict[str, Any]:
    """Validate a case manifest and return it unchanged when valid.

    The contract intentionally distinguishes *role* from *reference kind*. A PLUMES trace may be
    a software-regression oracle, while a laboratory dataset may later be a hold-back. Using a
    case for calibration does not allow it to be relabelled as independent hold-back evidence.
    """
    if not isinstance(manifest, dict):
        raise ManifestError("manifest: expected an object")

    if _require(manifest, "schema_version", "manifest") != 1:
        raise ManifestError("manifest.schema_version: only version 1 is supported")

    _require_nonempty_string(_require(manifest, "case_id", "manifest"), "manifest.case_id")
    _require_nonempty_string(_require(manifest, "purpose", "manifest"), "manifest.purpose")

    role = _require_nonempty_string(_require(manifest, "role", "manifest"), "manifest.role")
    if role not in _ALLOWED_ROLES:
        raise ManifestError(f"manifest.role: unsupported role {role!r}")

    reference = _require(manifest, "reference", "manifest")
    if not isinstance(reference, dict):
        raise ManifestError("manifest.reference: expected an object")
    kind = _require_nonempty_string(
        _require(reference, "kind", "manifest.reference"), "manifest.reference.kind"
    )
    if kind not in _ALLOWED_REFERENCE_KINDS:
        raise ManifestError(f"manifest.reference.kind: unsupported kind {kind!r}")
    _require_nonempty_string(
        _require(reference, "identity", "manifest.reference"), "manifest.reference.identity"
    )

    raw_outputs = _require(manifest, "raw_outputs", "manifest")
    if not isinstance(raw_outputs, list) or not raw_outputs:
        raise ManifestError("manifest.raw_outputs: expected a non-empty list")
    for index, artifact in enumerate(raw_outputs):
        _validate_artifact(artifact, f"manifest.raw_outputs[{index}]")

    inputs = manifest.get("inputs", [])
    if not isinstance(inputs, list):
        raise ManifestError("manifest.inputs: expected a list")
    for index, artifact in enumerate(inputs):
        _validate_artifact(artifact, f"manifest.inputs[{index}]")

    normalization = _require(manifest, "normalization", "manifest")
    if not isinstance(normalization, dict):
        raise ManifestError("manifest.normalization: expected an object")
    _require_nonempty_string(
        _require(normalization, "parser", "manifest.normalization"),
        "manifest.normalization.parser",
    )
    coordinates = _require(normalization, "coordinates", "manifest.normalization")
    if coordinates != "surface_zero_z_positive_up":
        raise ManifestError(
            "manifest.normalization.coordinates: REF-1 PLUMES normalization requires "
            "'surface_zero_z_positive_up'"
        )

    return manifest


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Load and validate one JSON reference-case manifest."""
    parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_manifest(parsed)
