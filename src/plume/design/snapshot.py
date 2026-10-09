"""Pinned, provenance-bearing provider snapshot for one design timestamp.

The only provider I/O in DESIGN-1 is here. Evaluation never reloads a provider.
Inline profile temperature is in-situ ITS-90; salinity is Practical Salinity.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..config import LoadedConfig
from ..errors import ProviderDataError
from ..providers import ProviderContext, ProviderResult, load_provider


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=False).encode()).hexdigest()


def _timestamp(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("timezone missing")
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (ValueError, TypeError, AttributeError) as exc:
        raise ProviderDataError("design timestamp must be timezone-aware ISO-8601") from exc


def _profile(result: ProviderResult, key: str, water_depth_m: float) -> tuple[tuple[float, float], ...]:
    if result.data_kind != "depth_profile":
        raise ProviderDataError(f"{key}: expected a depth_profile, got {result.data_kind}")
    pairs = tuple((float(row["depth_m"]), float(row["value"])) for row in result.records)
    if (len(pairs) < 2 or any(not all(math.isfinite(v) for v in pair) for pair in pairs)
            or abs(pairs[0][0]) > 1e-8 or abs(pairs[-1][0] - water_depth_m) > 1e-8
            or any(b[0] <= a[0] for a, b in zip(pairs, pairs[1:]))):
        raise ProviderDataError(f"{key}: profile must cover 0 and water depth with increasing finite depths")
    if key == "salinity_profile_psu" and any(v < 0 for _, v in pairs):
        raise ProviderDataError("Practical Salinity must be non-negative")
    return pairs


def _scalar(result: ProviderResult, key: str, at_utc: str) -> float:
    if result.data_kind == "scalar":
        value = result.records[0]["value"]
    elif result.data_kind == "scalar_time_series":
        matches = [record["value"] for record in result.records if record["time"] == at_utc]
        if len(matches) != 1:
            raise ProviderDataError(f"{key}: no exact sample at {at_utc}; temporal interpolation is not implemented")
        value = matches[0]
    else:
        raise ProviderDataError(f"{key}: expected scalar or scalar_time_series, got {result.data_kind}")
    number = float(value)
    if not math.isfinite(number):
        raise ProviderDataError(f"{key}: value must be finite")
    return number


@dataclass(frozen=True)
class PinnedSnapshot:
    """Raw user-facing profile quantities; TEOS-10 conversion happens per evaluation."""

    at_utc: str
    site: dict[str, float]
    ambient_spec_sha256: str
    source_specs: dict[str, dict[str, Any]]
    temperature_profile_C: tuple[tuple[float, float], ...]
    salinity_profile_psu: tuple[tuple[float, float], ...]
    current_east_north_mps: tuple[float, float]
    source_scalars: dict[str, float]
    providers: dict[str, dict[str, Any]]
    snapshot_sha256: str

    def payload(self) -> dict[str, Any]:
        return {
            "at_utc": self.at_utc,
            "site": self.site,
            "ambient_spec_sha256": self.ambient_spec_sha256,
            "source_specs": self.source_specs,
            "temperature_profile_C": [list(x) for x in self.temperature_profile_C],
            "salinity_profile_psu": [list(x) for x in self.salinity_profile_psu],
            "current_east_north_mps": list(self.current_east_north_mps),
            "source_scalars": self.source_scalars,
            "providers": self.providers,
        }

    def as_record(self) -> dict[str, Any]:
        return {**self.payload(), "snapshot_sha256": self.snapshot_sha256, "qualification": "UNVALIDATED"}

    @classmethod
    def from_record(cls, raw: Mapping[str, Any]) -> "PinnedSnapshot":
        keys = ("at_utc", "site", "ambient_spec_sha256", "source_specs", "temperature_profile_C",
                "salinity_profile_psu", "current_east_north_mps", "source_scalars", "providers")
        try:
            data = {key: raw[key] for key in keys}
            claimed = str(raw["snapshot_sha256"])
            if _digest(data) != claimed:
                raise ProviderDataError("saved snapshot identity does not match its content")
            return cls(
                at_utc=_timestamp(data["at_utc"]), site=dict(data["site"]),
                ambient_spec_sha256=str(data["ambient_spec_sha256"]),
                source_specs=dict(data["source_specs"]),
                temperature_profile_C=tuple(tuple(float(v) for v in row) for row in data["temperature_profile_C"]),
                salinity_profile_psu=tuple(tuple(float(v) for v in row) for row in data["salinity_profile_psu"]),
                current_east_north_mps=tuple(float(v) for v in data["current_east_north_mps"]),
                source_scalars={k: float(v) for k, v in data["source_scalars"].items()},
                providers=dict(data["providers"]), snapshot_sha256=claimed,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderDataError("invalid saved design snapshot") from exc


def pin_snapshot(config: LoadedConfig, *, at_utc: str | None = None) -> PinnedSnapshot:
    """Load each deterministic source/ambient provider exactly once for a design pin."""
    forcing = config.normalized["forcing"]
    when = _timestamp(at_utc or forcing["clock"]["start"])
    if not (forcing["clock"]["start"] <= when <= forcing["clock"]["end"]):
        raise ProviderDataError("design timestamp is outside the configured forcing clock")
    sources = forcing["source"]
    ambient = forcing["ambient"]
    required_source = {"flow_m3h"}
    allowed_source = {"flow_m3h", "delta_T_C", "discharge_temperature_C", "salinity_psu"}
    if (not required_source.issubset(sources) or
            ("delta_T_C" in sources) == ("discharge_temperature_C" in sources) or
            set(sources) - allowed_source):
        raise ProviderDataError("DESIGN-1 source requires flow_m3h and exactly one of delta_T_C / discharge_temperature_C (optional salinity_psu)")
    if set(ambient) != {"temperature_profile_C", "salinity_profile_psu", "current_profile"}:
        raise ProviderDataError("DESIGN-1 ambient requires temperature_profile_C, salinity_profile_psu and current_profile")

    context = ProviderContext(config_dir=Path(config.source_dir))
    outputs: dict[str, ProviderResult] = {}
    providers: dict[str, dict[str, Any]] = {}
    for group, descriptors in (("source", sources), ("ambient", ambient)):
        for key, spec in sorted(descriptors.items()):
            result = load_provider(spec, context=context)
            outputs[f"{group}.{key}"] = result
            providers[f"forcing.{group}.{key}"] = result.manifest_summary()

    water_depth = config.normalized["site"]["water_depth_m"]
    temp = _profile(outputs["ambient.temperature_profile_C"], "temperature_profile_C", water_depth)
    salt = _profile(outputs["ambient.salinity_profile_psu"], "salinity_profile_psu", water_depth)
    current = outputs["ambient.current_profile"]
    if current.data_kind != "vector_constant":
        raise ProviderDataError("DESIGN-1 current_profile requires constant_vector until depth-vector providers are implemented")
    east = float(current.records[0]["u_east_mps"])
    north = float(current.records[0]["v_north_mps"])
    if not (math.isfinite(east) and math.isfinite(north)):
        raise ProviderDataError("current components must be finite")
    scalars = {key: _scalar(outputs[f"source.{key}"], key, when) for key in sources}
    if scalars["flow_m3h"] <= 0 or ("salinity_psu" in scalars and scalars["salinity_psu"] < 0):
        raise ProviderDataError("source flow must be positive and Practical Salinity non-negative")
    payload = {
        "at_utc": when,
        "site": dict(config.normalized["site"]),
        "ambient_spec_sha256": _digest(ambient),
        "source_specs": {k: dict(v) for k, v in sources.items()},
        "temperature_profile_C": [list(row) for row in temp],
        "salinity_profile_psu": [list(row) for row in salt],
        "current_east_north_mps": [east, north],
        "source_scalars": scalars,
        "providers": providers,
    }
    return PinnedSnapshot.from_record({**payload, "snapshot_sha256": _digest(payload)})
