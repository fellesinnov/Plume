"""TIME-1C bounded, headless quasi-steady near-field replay.

A run always binds a locked project revision to the ORIGINAL recorded plant
forcing, the acquired ocean history SHA and an immutable output directory.
NO regulatory criterion is evaluated in this source slice; all metrics are
UNVALIDATED sampled near-field indicators, not compliance verdicts.
"""
from __future__ import annotations

import copy
import csv
import json
import math
import os
import uuid
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Callable

import numpy as np

from .. import __version__
from ..config import LoadedConfig, normalize_config
from ..design import evaluate_design
from ..design.projects import DesignProject, ProjectStore
from ..design.snapshot import _digest
from ..errors import ProviderDataError, WorkspaceError
from ..history import HistoricalForcing
from ..workspace import _detect_git_sha


@dataclass(frozen=True)
class RunPreflight:
    project_id: str
    locked_revision_id: str
    history_sha256: str
    original_source_spec_sha256: str
    clock_steps: int
    available_steps: int
    missing_steps: int
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class HistoricalRun:
    run_id: str
    path: Path
    manifest: dict[str, Any]
    summary: dict[str, Any]


def restored_forcing_config(project: DesignProject, store: ProjectStore) -> LoadedConfig:
    """Recover time-varying *plant* descriptors from the locked snapshot.

    DESIGN-1's selected design can intentionally overwrite flow/T descriptors
    with one constant source state. Using that source state for a full year's
    replay would be silently false. The pinned snapshot preserves the original
    provider descriptor (relative to the current project config directory).
    """
    if not project.is_locked or not project.locked_revision_id:
        raise WorkspaceError("save a locked design revision before replay")
    current = store.open(project.project_id)
    if current.locked_revision_id != project.locked_revision_id or current.config.sha256 != project.config.sha256:
        raise WorkspaceError("project revision changed; reopen before historical replay")
    locked = store.load_locked_snapshot(current)
    if locked is None:
        raise WorkspaceError("locked project snapshot unavailable")
    locked.verify_identity()
    if (locked.site != current.config.normalized["site"] or
            _digest(current.config.normalized["forcing"]["ambient"]) != locked.ambient_spec_sha256):
        raise WorkspaceError("locked project no longer matches original pinned ambient")
    source = copy.deepcopy(locked.source_specs)
    if "flow_m3h" not in source or (("delta_T_C" in source) == ("discharge_temperature_C" in source)):
        raise ProviderDataError("locked design lacks original historical plant source descriptors")
    raw = copy.deepcopy(current.config.normalized)
    raw["forcing"]["source"] = source
    normalized = normalize_config(raw)
    # Intentional: source_path is current project.yaml; its relative CSV paths
    # were rebased to that directory at ProjectStore.create/save time.
    return LoadedConfig(current.config.source_path, normalized, _digest(normalized))


def preflight_history(project: DesignProject, store: ProjectStore, history: HistoricalForcing) -> RunPreflight:
    config = restored_forcing_config(project, store)
    history.verify_identity()
    history._require_config(config)  # request equality includes original time-varying source, site and clock
    if not history.available_times:
        raise ProviderDataError("historical period contains no complete forcing states")
    original = config.normalized["forcing"]["source"]
    warnings = ["UNVALIDATED MODEL/FIELD: near-field slice indicators; NOT a permit compliance assessment"]
    for name, spec in sorted(original.items()):
        if spec["provider"] == "constant":
            warnings.append(f"Plant source {name} is explicitly configured constant throughout the selected history")
    if history.missing_by_time:
        warnings.append(f"{len(history.missing_by_time)} forcing slots are missing; no temporal interpolation")
    return RunPreflight(project.project_id, str(project.locked_revision_id), history.data_sha256,
                        _digest(original), len(history.clock_times), len(history.available_times),
                        len(history.missing_by_time), tuple(warnings))


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"max": None, "p95": None, "p99": None, "mean": None}
    return {"max": float(max(values)), "p95": float(np.percentile(values, 95)),
            "p99": float(np.percentile(values, 99)), "mean": float(mean(values))}


def _atomic_json(path: Path, content: dict[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(content, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def run_history(project: DesignProject, store: ProjectStore, history: HistoricalForcing, *,
                max_steps: int = 24, evaluator: Callable[..., Any] = evaluate_design,
                section_resolution: tuple[int, int] = (41, 31),
                plan_resolution: tuple[int, int] = (41, 31),
                retain_example_fields: bool = False,
                now: datetime | None = None) -> HistoricalRun:
    """Explicit bounded replay; 8,760-step runs require choosing that limit.

    Purely quasi-steady: each exact UTC slot solved independently, no inferred
    far field, no plume time memory, no permit pass/fail or interpolated gap.
    Failures create explicit FAILED manifests; existing runs are not replaced.
    """
    preflight = preflight_history(project, store, history)
    if type(max_steps) is not int or not 1 <= max_steps <= 100000:
        raise WorkspaceError("max_steps must be 1..100000 integer")
    candidate = restored_forcing_config(project, store)
    slots = history.clock_times[:max_steps]
    if not slots:
        raise WorkspaceError("no historical slots selected")
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    label = timestamp.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_id = "time1-" + label
    directory = project.project_dir / "runs" / run_id
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise WorkspaceError("unable to create unique historical run directory") from exc
    manifest: dict[str, Any] = {
        "format_version": 1, "stage": "RUNNING", "run_id": run_id,
        "created_utc": timestamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "software": {"version": __version__, "git_sha": os.getenv("PLUME_GIT_SHA") or _detect_git_sha(project.config.source_dir) or "unknown"},
        "project": {"id": project.project_id, "locked_revision_id": project.locked_revision_id,
                    "locked_config_sha256": project.config.sha256},
        "forcing": {"original_source_specs_sha256": preflight.original_source_spec_sha256,
                    "history_request_sha256": history.request_sha256,
                    "history_data_sha256": history.data_sha256,
                    "selected_clock_start": slots[0], "selected_clock_end_inclusive": slots[-1],
                    "requested_steps": len(slots), "total_clock_steps": preflight.clock_steps},
        "model": {"outfall": project.config.normalized["outfall"],
                  "near_field": project.config.normalized["model"].get("near_field", {}),
                  "reconstruction": "FIELD-1", "physical_status": "UNVALIDATED"},
        "source": {"original_time_varying_descriptors": candidate.normalized["forcing"]["source"],
                   "locked_design_descriptors": project.config.normalized["forcing"]["source"]},
        "criteria": {"configuration": project.config.normalized["criteria"],
                     "status": "NOT_ASSESSED", "legal_pass_fail": None},
        "retention": {"fields": "selected" if retain_example_fields else "none",
                      "normalized_config": True, "timestep_metrics": True},
        "warnings": list(preflight.warnings), "outputs": {},
    }
    _atomic_json(directory / "manifest.json", manifest)
    _atomic_json(directory / "config.normalized.json", candidate.normalized)
    rows: list[dict[str, Any]] = []
    saved_fields: list[tuple[str, Any]] = []
    try:
        for when in slots:
            if when in history.missing_by_time:
                rows.append({"time_utc": when, "status": "MISSING", "missing": list(history.missing_by_time[when]),
                             "snapshot_sha256": None, "section_peak_delta_T_C": None,
                             "plan_peak_delta_T_C": None, "plan_threshold_radius_m": None,
                             "bulk_dilution": None, "criterion_status": "NOT_ASSESSED"})
                continue
            pinned = history._snapshot_unchecked(when)  # verified once by preflight; O(depth levels) per slot
            evaluated = evaluator(candidate.normalized, pinned,
                                  section_resolution=section_resolution,
                                  plan_resolution=plan_resolution)
            metrics = evaluated.metrics
            for key in ("section_peak_delta_T_C", "plan_peak_delta_T_C", "final_bulk_dilution"):
                value = float(metrics[key])
                if not math.isfinite(value):
                    raise ProviderDataError(f"model produced nonfinite {key} at {when}")
            row = {"time_utc": when, "status": "SOLVED", "missing": [],
                   "snapshot_sha256": pinned.snapshot_sha256,
                   "section_peak_delta_T_C": float(metrics["section_peak_delta_T_C"]),
                   "plan_peak_delta_T_C": float(metrics["plan_peak_delta_T_C"]),
                   "plan_threshold_radius_m": metrics.get("plan_threshold_farthest_radius_m"),
                   "bulk_dilution": float(metrics["final_bulk_dilution"]),
                   "termination": str(metrics.get("termination_reason", "unknown")),
                   "model_status": "UNVALIDATED", "criterion_status": "NOT_ASSESSED"}
            rows.append(row)
            if retain_example_fields and (len(saved_fields) == 0 or row["section_peak_delta_T_C"] > saved_fields[0][1].metrics["section_peak_delta_T_C"]):
                saved_fields = [(when, evaluated)]
        stats = {
            "selected_steps": len(slots), "solved_steps": sum(r["status"] == "SOLVED" for r in rows),
            "missing_steps": sum(r["status"] == "MISSING" for r in rows),
            "complete_historical_period": len(slots) == len(history.clock_times) and not history.missing_by_time,
            "section_peak_delta_T_C": _stats([r["section_peak_delta_T_C"] for r in rows if r["status"] == "SOLVED"]),
            "plan_peak_delta_T_C": _stats([r["plan_peak_delta_T_C"] for r in rows if r["status"] == "SOLVED"]),
            "scope": "MODEL-1/FIELD-1 discrete near-field slice indicators, UNVALIDATED",
            "criterion_status": "NOT_ASSESSED", "permit_verdict": None,
        }
        _atomic_json(directory / "summary.json", stats)
        _atomic_json(directory / "timestep_metrics.json", {"rows": rows})
        with (directory / "timestep_metrics.csv").open("w", newline="", encoding="utf-8") as output:
            columns = ["time_utc", "status", "snapshot_sha256", "section_peak_delta_T_C",
                       "plan_peak_delta_T_C", "plan_threshold_radius_m", "bulk_dilution", "criterion_status"]
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key) for key in columns})
        if saved_fields:
            from ..render import render_field_pair
            from matplotlib import pyplot as plt
            for stamp, evaluated in saved_fields:
                fig = render_field_pair(evaluated.section, evaluated.plan,
                                        threshold_delta_T_C=float(evaluated.metrics["threshold_delta_T_C"]),
                                        title=f"UNVALIDATED selected historical state {stamp}")
                try:
                    fig.savefig(directory / "selected-field.png", dpi=120)
                finally:
                    plt.close(fig)
        hashes = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                  for name in ("config.normalized.json", "timestep_metrics.json", "timestep_metrics.csv", "summary.json")}
        if saved_fields:
            hashes["selected-field.png"] = hashlib.sha256((directory / "selected-field.png").read_bytes()).hexdigest()
        manifest["artifact_sha256"] = hashes
        manifest["stage"] = "COMPLETED"
        manifest["summary"] = stats
        manifest["outputs"] = {"config": "config.normalized.json", "metrics_csv": "timestep_metrics.csv",
                               "metrics_json": "timestep_metrics.json", "summary": "summary.json",
                               "selected_field_png": "selected-field.png" if saved_fields else None}
        _atomic_json(directory / "manifest.json", manifest)
        return HistoricalRun(run_id, directory, manifest, stats)
    except Exception as exc:
        manifest["stage"] = "FAILED"
        # Avoid leaking third-party client URLs potentially containing tokens.
        manifest["error_type"] = type(exc).__name__
        _atomic_json(directory / "manifest.json", manifest)
        raise


def load_historical_run(project: DesignProject, run_id: str) -> HistoricalRun:
    """Read-only result with project/revision and stored SHA guards."""
    if not run_id.startswith("time1-") or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in run_id):
        raise WorkspaceError("invalid run identity")
    root = project.project_dir / "runs" / run_id
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        if manifest["run_id"] != run_id or manifest["project"]["id"] != project.project_id:
            raise WorkspaceError("run manifest identity does not match project")
        if manifest["stage"] != "COMPLETED":
            raise WorkspaceError("run is not completed")
        digests = manifest["artifact_sha256"]
        if not isinstance(digests, dict) or not digests:
            raise WorkspaceError("historical run has no output integrity manifest")
        for name, sha in digests.items():
            if name not in {"config.normalized.json", "timestep_metrics.json", "timestep_metrics.csv", "summary.json", "selected-field.png"}:
                raise WorkspaceError("unexpected historical run artifact path")
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != sha:
                raise WorkspaceError(f"stored historical run artifact bytes changed: {name}")
        summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise WorkspaceError("stored historical run unavailable or invalid") from exc
    return HistoricalRun(run_id, root, manifest, summary)
