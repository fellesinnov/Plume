"""Workspace-local Design Studio projects and immutable-ish locked revisions.

No UI imports. Project/config state lives under the chosen ignored workspace;
source/provider data are never copied, deleted, or modified by a design save.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from .. import __version__
from ..config import LoadedConfig, load_config, normalize_config
from ..errors import WorkspaceError
from .evaluate import DesignEvaluation
from .snapshot import PinnedSnapshot, _digest

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_REV = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")


def _write(path: Path, content: str) -> None:
    temp = path.with_name(path.name + ".tmp")
    try:
        temp.write_text(content, encoding="utf-8")
        temp.replace(path)
    except OSError as exc:
        temp.unlink(missing_ok=True)
        raise WorkspaceError(f"unable to persist {path}") from exc


def _yaml(path: Path, data: Mapping[str, Any]) -> None:
    _write(path, yaml.safe_dump(dict(data), sort_keys=False, allow_unicode=True))


def _json(path: Path, data: Mapping[str, Any]) -> None:
    _write(path, json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n")


def _rebase_paths(normalized: Mapping[str, Any], source_dir: Path, dest_dir: Path,
                  workspace_root: Path) -> dict[str, Any]:
    """Keep local descriptor paths correct when moving a config within workspace."""
    updated = copy.deepcopy(dict(normalized))
    updated["workspace"]["root"] = Path(os.path.relpath(workspace_root, dest_dir)).as_posix()
    for group in ("source", "ambient"):
        for spec in updated["forcing"][group].values():
            if spec["provider"] in {"csv", "csv_depth_profile"}:
                input_path = Path(spec["path"])
                full = (input_path if input_path.is_absolute() else source_dir / input_path).resolve()
                spec["path"] = Path(os.path.relpath(full, dest_dir)).as_posix()
    return normalize_config(updated)


def _git_identity() -> str:
    import os
    if os.getenv("PLUME_GIT_SHA"):
        return os.environ["PLUME_GIT_SHA"]
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True, timeout=2).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


@dataclass(frozen=True)
class DesignProject:
    project_dir: Path
    config: LoadedConfig
    locked_revision_id: str | None
    locked_config_sha256: str | None

    @property
    def project_id(self) -> str:
        return self.config.project_id

    @property
    def is_locked(self) -> bool:
        return self.locked_revision_id is not None


class ProjectStore:
    """Single-writer local project API; no lock acquisition or remote merge rights."""

    def __init__(self, workspace_root: str | Path):
        self.root = Path(workspace_root).expanduser().resolve()

    def _directory(self, project_id: str) -> Path:
        if not _ID.fullmatch(project_id):
            raise WorkspaceError("invalid project id")
        return self.root / "projects" / project_id

    def list_projects(self) -> tuple[str, ...]:
        folder = self.root / "projects"
        if not folder.exists():
            return ()
        return tuple(sorted(p.name for p in folder.iterdir()
                            if p.is_dir() and _ID.fullmatch(p.name)
                            and (p / "project.yaml").is_file()
                            and (p / "project-state.json").is_file()))

    def create(self, template: LoadedConfig, *, project_id: str, name: str,
               latitude_deg: float | None = None,
               longitude_deg: float | None = None) -> DesignProject:
        candidate = copy.deepcopy(template.normalized)
        candidate["project"] = {"id": project_id, "name": name}
        if latitude_deg is not None:
            candidate["site"]["latitude_deg"] = latitude_deg
        if longitude_deg is not None:
            candidate["site"]["longitude_deg"] = longitude_deg
        candidate = normalize_config(candidate)
        directory = self._directory(project_id)
        try:
            directory.mkdir(parents=True, exist_ok=False)
            (directory / "revisions").mkdir()
            (directory / "runs").mkdir()
        except FileExistsError as exc:
            raise WorkspaceError(f"project already exists: {project_id}") from exc
        except OSError as exc:
            raise WorkspaceError(f"could not create project: {project_id}") from exc
        local = _rebase_paths(candidate, template.source_dir, directory, self.root)
        _yaml(directory / "project.yaml", local)
        _json(directory / "project-state.json", {"version": 1, "locked_revision_id": None,
                                                  "locked_config_sha256": None})
        return self.open(project_id)

    def open(self, project_id: str) -> DesignProject:
        directory = self._directory(project_id)
        if not (directory / "project.yaml").is_file():
            raise WorkspaceError(f"project does not exist: {project_id}")
        try:
            config = load_config(directory / "project.yaml")
            state = json.loads((directory / "project-state.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkspaceError(f"invalid local project state: {project_id}") from exc
        if state.get("version") != 1:
            raise WorkspaceError("unsupported project state version")
        locked = state.get("locked_revision_id")
        if locked is not None and (not isinstance(locked, str) or not _REV.fullmatch(locked)
                                    or not (directory / "revisions" / locked / "snapshot.json").is_file()):
            raise WorkspaceError("project references a missing/invalid locked revision")
        sha = state.get("locked_config_sha256")
        if locked is not None and sha != config.sha256:
            raise WorkspaceError("locked project configuration has changed outside the revision store")
        if config.project_id != project_id:
            raise WorkspaceError("project id does not match its workspace directory")
        return DesignProject(directory, config, locked, sha)

    def load_locked_snapshot(self, project: DesignProject) -> PinnedSnapshot | None:
        if project.locked_revision_id is None:
            return None
        path = project.project_dir / "revisions" / project.locked_revision_id / "snapshot.json"
        try:
            return PinnedSnapshot.from_record(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkspaceError("cannot load locked design snapshot") from exc

    def save_revision(self, project: DesignProject, evaluation: DesignEvaluation, *,
                      now: datetime | None = None) -> DesignProject:
        """Persist candidate, source snapshot and metrics; advance lock *last*."""
        current = self.open(project.project_id)
        if current.locked_revision_id != project.locked_revision_id:
            raise WorkspaceError("locked revision changed since project was opened; reopen before saving")
        evaluation.snapshot.verify_identity()
        raw = evaluation.normalized_config
        if raw["project"]["id"] != project.project_id or raw["site"] != evaluation.snapshot.site:
            raise WorkspaceError("design project/site mismatch")
        if _digest(raw["forcing"]["ambient"]) != evaluation.snapshot.ambient_spec_sha256:
            raise WorkspaceError("ambient changed since pin; repin before saving")
        timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        rid = timestamp.strftime("%Y%m%dT%H%M%SZ") + "-" + evaluation.config_sha256[:8]
        destination = project.project_dir / "revisions" / rid
        try:
            destination.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise WorkspaceError("design revision already exists; no revision overwritten") from exc
        except OSError as exc:
            raise WorkspaceError("cannot create design revision") from exc
        revision_config = _rebase_paths(raw, project.config.source_dir, destination, self.root)
        current_config = _rebase_paths(raw, project.config.source_dir, project.project_dir, self.root)
        _yaml(destination / "config.normalized.yaml", revision_config)
        _json(destination / "snapshot.json", evaluation.snapshot.as_record())
        _json(destination / "evaluation.json", {
            **evaluation.record(),
            "revision_id": rid,
            "saved_revision_config_sha256": _digest(revision_config),
            "saved_project_config_sha256": _digest(current_config),
            "created_utc": timestamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "software": {"version": __version__, "git_sha": _git_identity()},
            "coordinates": {"frame": "ENU", "depth_positive": "down",
                            "azimuth": "clockwise_from_true_north"},
            "criterion_verdict": "NOT_ASSESSED",
            "qualification_gates": ["MODEL-CLOSURE-1", "FIELD-PROFILE-1", "MODEL-TOL-1"],
        })
        # Only after revision evidence exists is a project lock replaced.
        _yaml(project.project_dir / "project.yaml", current_config)
        _json(project.project_dir / "project-state.json", {
            "version": 1, "locked_revision_id": rid,
            "locked_config_sha256": _digest(current_config),
        })
        return self.open(project.project_id)


def export_portable_yaml(project: DesignProject) -> str:
    """Portable locked *provider config*; cannot silently orphan local CSV paths."""
    if not project.is_locked:
        raise WorkspaceError("save a locked revision before exporting")
    data = copy.deepcopy(project.config.normalized)
    if any(spec["provider"] in {"csv", "csv_depth_profile"}
           for group in ("source", "ambient")
           for spec in data["forcing"][group].values()):
        raise WorkspaceError("file-backed provider config requires companion CSV files; export the pinned snapshot instead")
    data["workspace"]["root"] = "./workspace"
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def export_snapshot_yaml(project: DesignProject, snapshot: PinnedSnapshot) -> str:
    """Self-contained, one-hour *design snapshot* config; not historical forcing."""
    from datetime import timedelta

    if not project.is_locked:
        raise WorkspaceError("save a locked revision before exporting")
    snapshot.verify_identity()
    saved_path = project.project_dir / "revisions" / project.locked_revision_id / "snapshot.json"
    try:
        stored = PinnedSnapshot.from_record(json.loads(saved_path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError("locked snapshot cannot be read") from exc
    if snapshot.snapshot_sha256 != stored.snapshot_sha256:
        raise WorkspaceError("export requires the selected locked revision's pinned snapshot")
    if project.config.normalized["site"] != snapshot.site or _digest(
        project.config.normalized["forcing"]["ambient"]
    ) != snapshot.ambient_spec_sha256:
        raise WorkspaceError("saved config and pinned snapshot do not agree")
    data = copy.deepcopy(project.config.normalized)
    t = datetime.fromisoformat(snapshot.at_utc.replace("Z", "+00:00"))
    data["forcing"]["clock"] = {
        "start": snapshot.at_utc,
        "end": (t + timedelta(hours=1)).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "step": "PT1H",
    }
    data["forcing"]["ambient"] = {
        "temperature_profile_C": {"provider": "inline_profile", "levels": [
            {"depth_m": d, "value": v} for d, v in snapshot.temperature_profile_C]},
        "salinity_profile_psu": {"provider": "inline_profile", "levels": [
            {"depth_m": d, "value": v} for d, v in snapshot.salinity_profile_psu]},
        "current_profile": {"provider": "constant_vector",
                            "u_east_mps": snapshot.current_east_north_mps[0],
                            "v_north_mps": snapshot.current_east_north_mps[1]},
    }
    data["forcing"]["source"] = {
        key: (spec if spec["provider"] == "constant" else
              {"provider": "constant", "value": snapshot.source_scalars[key]})
        for key, spec in data["forcing"]["source"].items()
    }
    data["workspace"]["root"] = "./workspace"
    return yaml.safe_dump(normalize_config(data), sort_keys=False, allow_unicode=True)
