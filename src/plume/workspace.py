"""Workspace and run-manifest preparation."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from . import __version__
from .config import LoadedConfig
from .errors import WorkspaceError
from .providers import ProviderContext, load_provider


@dataclass(frozen=True)
class PreparedRun:
    run_id: str
    run_dir: Path
    manifest_path: Path
    normalized_config_path: Path
    manifest: dict[str, Any]


def resolve_workspace_root(config: LoadedConfig, override: str | Path | None = None) -> Path:
    if override is not None:
        root = Path(override).expanduser()
        return root.resolve()
    configured = Path(str(config.normalized["workspace"]["root"])).expanduser()
    if configured.is_absolute():
        return configured.resolve()
    return (config.source_dir / configured).resolve()


def prepare_run(
    config: LoadedConfig,
    *,
    workspace_override: str | Path | None = None,
    run_id: str | None = None,
    git_sha: str | None = None,
    now: Callable[[], datetime] | None = None,
) -> PreparedRun:
    """Prepare immutable run evidence without invoking plume physics."""

    now_fn = now or (lambda: datetime.now(timezone.utc))
    created = now_fn().astimezone(timezone.utc)
    if run_id is None:
        run_id = f"{created.strftime('%Y%m%dT%H%M%SZ')}-{config.sha256[:8]}"
    _validate_run_id(run_id)

    workspace_root = resolve_workspace_root(config, workspace_override)
    provider_summaries, provider_warnings = _resolve_provider_summaries(config)

    run_dir = workspace_root / "projects" / config.project_id / "runs" / run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise WorkspaceError(f"run directory already exists: {run_dir}") from exc
    except OSError as exc:
        raise WorkspaceError(f"could not create run directory: {run_dir}") from exc

    for name in ("inputs", "results", "plots", "animations", "logs"):
        (run_dir / name).mkdir()

    resolved_git_sha = git_sha or _detect_git_sha(config.source_dir)
    warnings = list(provider_warnings)
    if resolved_git_sha is None:
        resolved_git_sha = os.getenv("PLUME_GIT_SHA") or "unknown"
        if resolved_git_sha == "unknown":
            warnings.append("Plume git SHA could not be detected; set PLUME_GIT_SHA for packaged runs.")

    normalized_path = run_dir / "config.normalized.yaml"
    manifest_path = run_dir / "manifest.json"
    _atomic_text(
        normalized_path,
        yaml.safe_dump(
            config.normalized,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ),
    )

    manifest = {
        "manifest_version": 1,
        "stage": "prepared",
        "run_id": run_id,
        "created_utc": created.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "project": {"id": config.project_id, "name": config.normalized["project"]["name"]},
        "config": {
            "source_path": str(config.source_path),
            "schema_version": config.normalized["schema_version"],
            "normalized_sha256": config.sha256,
        },
        "software": {
            "package": "plume-engine",
            "version": __version__,
            "git_sha": resolved_git_sha,
        },
        "coordinates": {
            "frame": "ENU",
            "x": "east",
            "y": "north",
            "z": "up",
            "depth_positive": "down",
            "azimuth": "clockwise_from_true_north",
            "vertical_angle": "from_horizontal_positive_up",
        },
        "outfall": dict(config.normalized["outfall"]),
        "providers": provider_summaries,
        "criteria": config.normalized["criteria"],
        "workspace": {
            "resolved_root": str(workspace_root),
            "shared_provider_cache": config.normalized["workspace"]["shared_provider_cache"],
            "override_used": workspace_override is not None,
        },
        "warnings": warnings,
        "outputs": {
            "normalized_config": normalized_path.name,
            "manifest": manifest_path.name,
        },
    }
    _atomic_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return PreparedRun(
        run_id=run_id,
        run_dir=run_dir,
        manifest_path=manifest_path,
        normalized_config_path=normalized_path,
        manifest=manifest,
    )


def _resolve_provider_summaries(config: LoadedConfig) -> tuple[dict[str, Any], list[str]]:
    context = ProviderContext(config_dir=config.source_dir)
    summaries: dict[str, Any] = {}
    warnings: list[str] = []
    forcing = config.normalized["forcing"]
    for group in ("source", "ambient"):
        for name, spec in forcing[group].items():
            key = f"forcing.{group}.{name}"
            result = load_provider(spec, context=context)
            summary = result.manifest_summary()
            summaries[key] = summary
            warnings.extend(f"{key}: {warning}" for warning in result.provenance.warnings)
    return summaries, warnings


def _detect_git_sha(start_dir: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(start_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = completed.stdout.strip()
    return sha or None


def _validate_run_id(run_id: str) -> None:
    if not run_id or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for ch in run_id):
        raise WorkspaceError("run_id may contain only letters, numbers, '_' and '-'")


def _atomic_text(path: Path, content: str) -> None:
    temp = path.with_name(path.name + ".tmp")
    try:
        temp.write_text(content, encoding="utf-8")
        temp.replace(path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise WorkspaceError(f"could not write {path}") from exc
