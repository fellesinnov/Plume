"""Deterministic local providers used before external data services are introduced."""

from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..errors import ConfigError, ProviderDataError
from .base import ProviderContext, ProviderProvenance, ProviderResult


def _reject_unknown(raw: Mapping[str, Any], allowed: set[str], context: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ConfigError(f"{context} has unsupported field(s): {', '.join(unknown)}")


def _number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{context} must be a number")
    return float(value)


def _nonempty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context} must be a non-empty string")
    return value.strip()


def _portable_path(value: Any, context: str) -> str:
    text = _nonempty_string(value, context).replace("\\", "/")
    path = Path(text)
    if path.is_absolute():
        return path.as_posix()
    parts: list[str] = []
    for part in path.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if parts and parts[-1] != "..":
                parts.pop()
            else:
                parts.append(part)
        else:
            parts.append(part)
    return Path(*parts).as_posix() if parts else "."


class ConstantProvider:
    name = "constant"

    def normalize_spec(self, raw: Mapping[str, Any], *, context: str) -> dict[str, Any]:
        _reject_unknown(raw, {"provider", "value"}, context)
        if "value" not in raw:
            raise ConfigError(f"{context}.value is required")
        return {"provider": self.name, "value": _number(raw["value"], f"{context}.value")}

    def load(self, spec: Mapping[str, Any], *, context: ProviderContext) -> ProviderResult:
        del context
        value = float(spec["value"])
        return ProviderResult(
            data_kind="scalar",
            records=({"value": value},),
            provenance=ProviderProvenance(
                provider=self.name,
                source="config",
                request=dict(spec),
            ),
        )


class ConstantVectorProvider:
    name = "constant_vector"

    def normalize_spec(self, raw: Mapping[str, Any], *, context: str) -> dict[str, Any]:
        _reject_unknown(raw, {"provider", "u_east_mps", "v_north_mps"}, context)
        if "u_east_mps" not in raw or "v_north_mps" not in raw:
            raise ConfigError(f"{context} requires u_east_mps and v_north_mps")
        return {
            "provider": self.name,
            "u_east_mps": _number(raw["u_east_mps"], f"{context}.u_east_mps"),
            "v_north_mps": _number(raw["v_north_mps"], f"{context}.v_north_mps"),
        }

    def load(self, spec: Mapping[str, Any], *, context: ProviderContext) -> ProviderResult:
        del context
        return ProviderResult(
            data_kind="vector_constant",
            records=(
                {
                    "u_east_mps": float(spec["u_east_mps"]),
                    "v_north_mps": float(spec["v_north_mps"]),
                },
            ),
            provenance=ProviderProvenance(
                provider=self.name,
                source="config",
                request=dict(spec),
            ),
        )


class InlineProfileProvider:
    name = "inline_profile"

    def normalize_spec(self, raw: Mapping[str, Any], *, context: str) -> dict[str, Any]:
        _reject_unknown(raw, {"provider", "levels"}, context)
        levels = raw.get("levels")
        if not isinstance(levels, list) or not levels:
            raise ConfigError(f"{context}.levels must be a non-empty list")
        normalized: list[dict[str, float]] = []
        seen_depths: set[float] = set()
        for index, level in enumerate(levels):
            level_context = f"{context}.levels[{index}]"
            if not isinstance(level, Mapping):
                raise ConfigError(f"{level_context} must be a mapping")
            _reject_unknown(level, {"depth_m", "value"}, level_context)
            if "depth_m" not in level or "value" not in level:
                raise ConfigError(f"{level_context} requires depth_m and value")
            depth = _number(level["depth_m"], f"{level_context}.depth_m")
            value = _number(level["value"], f"{level_context}.value")
            if depth < 0:
                raise ConfigError(f"{level_context}.depth_m must be >= 0")
            if depth in seen_depths:
                raise ConfigError(f"{context}.levels contains duplicate depth_m {depth:g}")
            seen_depths.add(depth)
            normalized.append({"depth_m": depth, "value": value})
        normalized.sort(key=lambda item: item["depth_m"])
        return {"provider": self.name, "levels": normalized}

    def load(self, spec: Mapping[str, Any], *, context: ProviderContext) -> ProviderResult:
        del context
        records = tuple(dict(level) for level in spec["levels"])
        return ProviderResult(
            data_kind="depth_profile",
            records=records,
            provenance=ProviderProvenance(
                provider=self.name,
                source="config",
                request=dict(spec),
            ),
        )


class CsvProvider:
    """CSV scalar time-series provider for schema v1.

    More CSV shapes can be added behind the same provider interface without changing callers.
    """

    name = "csv"

    def normalize_spec(self, raw: Mapping[str, Any], *, context: str) -> dict[str, Any]:
        _reject_unknown(raw, {"provider", "path", "time_column", "value_column"}, context)
        required = ("path", "time_column", "value_column")
        missing = [key for key in required if key not in raw]
        if missing:
            raise ConfigError(f"{context} missing required field(s): {', '.join(missing)}")
        return {
            "provider": self.name,
            "path": _portable_path(raw["path"], f"{context}.path"),
            "time_column": _nonempty_string(raw["time_column"], f"{context}.time_column"),
            "value_column": _nonempty_string(raw["value_column"], f"{context}.value_column"),
        }

    def load(self, spec: Mapping[str, Any], *, context: ProviderContext) -> ProviderResult:
        configured = Path(str(spec["path"]))
        path = configured if configured.is_absolute() else context.config_dir / configured
        path = path.resolve()
        if not path.is_file():
            raise ProviderDataError(f"CSV provider file does not exist: {path}")
        raw_bytes = path.read_bytes()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        time_column = str(spec["time_column"])
        value_column = str(spec["value_column"])
        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            for required in (time_column, value_column):
                if required not in fieldnames:
                    raise ProviderDataError(
                        f"CSV provider file {path} is missing column {required!r}"
                    )
            previous_time: datetime | None = None
            for row_number, row in enumerate(reader, start=2):
                try:
                    when = _parse_timestamp(row[time_column])
                except (TypeError, ValueError) as exc:
                    raise ProviderDataError(
                        f"CSV provider file {path} row {row_number} has invalid timestamp"
                    ) from exc
                try:
                    value = float(row[value_column])
                except (TypeError, ValueError) as exc:
                    raise ProviderDataError(
                        f"CSV provider file {path} row {row_number} has invalid numeric value"
                    ) from exc
                if previous_time is not None and when <= previous_time:
                    raise ProviderDataError(
                        f"CSV provider file {path} timestamps must be strictly increasing"
                    )
                previous_time = when
                records.append({"time": _format_datetime(when), "value": value})
        if not records:
            raise ProviderDataError(f"CSV provider file {path} contains no data rows")
        return ProviderResult(
            data_kind="scalar_time_series",
            records=tuple(records),
            provenance=ProviderProvenance(
                provider=self.name,
                source=str(path),
                request=dict(spec),
                input_sha256=digest,
            ),
        )


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp is empty")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return dt.astimezone(timezone.utc)


def _format_datetime(value: datetime) -> str:
    value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")
