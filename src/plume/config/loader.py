"""Versioned Plume config loading and normalization."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..errors import ConfigError, UnsupportedSchemaVersionError
from ..outlets import normalize_outfall
from ..providers import normalize_provider_spec

_SCHEMA_VERSION = 1
_TOP_LEVEL_FIELDS = {
    "schema_version",
    "project",
    "site",
    "outfall",
    "forcing",
    "model",
    "criteria",
    "workspace",
    "outputs",
}
_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_DURATION_RE = re.compile(
    r"^P(?=.)(?:(?P<days>\d+(?:\.\d+)?)D)?(?:T(?=.)(?:(?P<hours>\d+(?:\.\d+)?)H)?(?:(?P<minutes>\d+(?:\.\d+)?)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)


@dataclass(frozen=True)
class LoadedConfig:
    source_path: Path
    normalized: dict[str, Any]
    sha256: str

    @property
    def source_dir(self) -> Path:
        return self.source_path.parent

    @property
    def project_id(self) -> str:
        return str(self.normalized["project"]["id"])

    def canonical_json(self) -> str:
        return json.dumps(self.normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_config(path: str | Path) -> LoadedConfig:
    source_path = Path(path).expanduser().resolve()
    if not source_path.is_file():
        raise ConfigError(f"config file does not exist: {source_path}")
    suffix = source_path.suffix.lower()
    try:
        text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"could not read config file: {source_path}") from exc

    try:
        if suffix == ".json":
            raw = json.loads(text)
        elif suffix in {".yaml", ".yml"}:
            raw = yaml.safe_load(text)
        else:
            raise ConfigError("config extension must be .yaml, .yml, or .json")
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"could not parse config file: {source_path}") from exc

    if not isinstance(raw, Mapping):
        raise ConfigError("config root must be a mapping")
    normalized = normalize_config(raw)
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return LoadedConfig(source_path=source_path, normalized=normalized, sha256=digest)


def normalize_config(raw: Mapping[str, Any]) -> dict[str, Any]:
    _reject_unknown(raw, _TOP_LEVEL_FIELDS, "config")
    missing = sorted(_TOP_LEVEL_FIELDS - set(raw))
    if missing:
        raise ConfigError(f"config missing required section(s): {', '.join(missing)}")

    version = raw.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise ConfigError("schema_version must be an integer")
    if version != _SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(
            f"unsupported schema_version {version!r}; supported: {_SCHEMA_VERSION}"
        )

    project = _normalize_project(raw["project"])
    site = _normalize_site(raw["site"])
    outfall = normalize_outfall(raw["outfall"], water_depth_m=site["water_depth_m"])
    forcing = _normalize_forcing(raw["forcing"])
    model = _plain_mapping(raw["model"], "model")
    criteria = _normalize_criteria(raw["criteria"])
    workspace = _normalize_workspace(raw["workspace"])
    outputs = _plain_mapping(raw["outputs"], "outputs")

    return {
        "schema_version": _SCHEMA_VERSION,
        "project": project,
        "site": site,
        "outfall": outfall,
        "forcing": forcing,
        "model": model,
        "criteria": criteria,
        "workspace": workspace,
        "outputs": outputs,
    }


def _normalize_project(raw: Any) -> dict[str, Any]:
    mapping = _mapping(raw, "project")
    _reject_unknown(mapping, {"id", "name"}, "project")
    project_id = _string(mapping.get("id"), "project.id")
    if not _PROJECT_ID_RE.fullmatch(project_id):
        raise ConfigError(
            "project.id must start with an alphanumeric character and contain only letters, numbers, '_' or '-'"
        )
    return {"id": project_id, "name": _string(mapping.get("name"), "project.name")}


def _normalize_site(raw: Any) -> dict[str, Any]:
    mapping = _mapping(raw, "site")
    _reject_unknown(mapping, {"latitude_deg", "longitude_deg", "water_depth_m"}, "site")
    latitude = _number(mapping.get("latitude_deg"), "site.latitude_deg")
    longitude = _number(mapping.get("longitude_deg"), "site.longitude_deg")
    water_depth = _number(mapping.get("water_depth_m"), "site.water_depth_m")
    if not -90 <= latitude <= 90:
        raise ConfigError("site.latitude_deg must be between -90 and 90")
    if not -180 <= longitude <= 180:
        raise ConfigError("site.longitude_deg must be between -180 and 180")
    if water_depth <= 0:
        raise ConfigError("site.water_depth_m must be > 0")
    return {
        "latitude_deg": latitude,
        "longitude_deg": longitude,
        "water_depth_m": water_depth,
    }


def _normalize_forcing(raw: Any) -> dict[str, Any]:
    mapping = _mapping(raw, "forcing")
    _reject_unknown(mapping, {"clock", "source", "ambient"}, "forcing")
    clock = _normalize_clock(mapping.get("clock"))
    source = _normalize_provider_group(mapping.get("source"), "forcing.source")
    ambient = _normalize_provider_group(mapping.get("ambient"), "forcing.ambient")
    if not source:
        raise ConfigError("forcing.source must contain at least one provider descriptor")
    if not ambient:
        raise ConfigError("forcing.ambient must contain at least one provider descriptor")
    return {"clock": clock, "source": source, "ambient": ambient}


def _normalize_clock(raw: Any) -> dict[str, Any]:
    mapping = _mapping(raw, "forcing.clock")
    _reject_unknown(mapping, {"start", "end", "step"}, "forcing.clock")
    start = _datetime_utc(mapping.get("start"), "forcing.clock.start")
    end = _datetime_utc(mapping.get("end"), "forcing.clock.end")
    if end <= start:
        raise ConfigError("forcing.clock.end must be after forcing.clock.start")
    step = _string(mapping.get("step"), "forcing.clock.step")
    match = _DURATION_RE.fullmatch(step)
    if not match:
        raise ConfigError("forcing.clock.step must be a positive ISO-8601 day/time duration")
    total_seconds = (
        float(match.group("days") or 0) * 86400
        + float(match.group("hours") or 0) * 3600
        + float(match.group("minutes") or 0) * 60
        + float(match.group("seconds") or 0)
    )
    if total_seconds <= 0:
        raise ConfigError("forcing.clock.step must be > 0")
    return {"start": _format_datetime(start), "end": _format_datetime(end), "step": step}


def _normalize_provider_group(raw: Any, context: str) -> dict[str, Any]:
    mapping = _mapping(raw, context)
    normalized: dict[str, Any] = {}
    for key in sorted(mapping):
        if not isinstance(key, str) or not key:
            raise ConfigError(f"{context} keys must be non-empty strings")
        normalized[key] = normalize_provider_spec(mapping[key], context=f"{context}.{key}")
    return normalized


def _normalize_criteria(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ConfigError("criteria must be a list")
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        context = f"criteria[{index}]"
        mapping = _mapping(item, context)
        plain = _plain_value(mapping, context)
        criterion_id = _string(plain.get("id"), f"{context}.id")
        _string(plain.get("type"), f"{context}.type")
        if criterion_id in seen_ids:
            raise ConfigError(f"criteria contains duplicate id {criterion_id!r}")
        seen_ids.add(criterion_id)
        normalized.append(plain)
    return normalized


def _normalize_workspace(raw: Any) -> dict[str, Any]:
    mapping = _mapping(raw, "workspace")
    _reject_unknown(mapping, {"root", "shared_provider_cache"}, "workspace")
    root = _string(mapping.get("root"), "workspace.root").replace("\\", "/")
    shared = mapping.get("shared_provider_cache")
    if not isinstance(shared, bool):
        raise ConfigError("workspace.shared_provider_cache must be boolean")
    return {"root": root, "shared_provider_cache": shared}


def _plain_mapping(raw: Any, context: str) -> dict[str, Any]:
    mapping = _mapping(raw, context)
    return _plain_value(mapping, context)


def _plain_value(value: Any, context: str) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return _format_datetime(_datetime_utc(value, context))
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise ConfigError(f"{context} mapping keys must be strings")
            result[key] = _plain_value(value[key], f"{context}.{key}")
        return result
    if isinstance(value, list):
        return [_plain_value(item, f"{context}[]") for item in value]
    raise ConfigError(f"{context} contains unsupported value type {type(value).__name__}")


def _mapping(raw: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping):
        raise ConfigError(f"{context} must be a mapping")
    return raw


def _reject_unknown(raw: Mapping[str, Any], allowed: set[str], context: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ConfigError(f"{context} has unsupported field(s): {', '.join(unknown)}")


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context} must be a non-empty string")
    return value.strip()


def _number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{context} must be a number")
    return float(value)


def _datetime_utc(value: Any, context: str) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ConfigError(f"{context} must be an ISO-8601 timestamp") from exc
    else:
        raise ConfigError(f"{context} must be an ISO-8601 timestamp")
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ConfigError(f"{context} must include a timezone")
    return dt.astimezone(timezone.utc)


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
