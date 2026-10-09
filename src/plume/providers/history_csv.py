"""Strict deterministic CSV sources for time/depth-resolved ocean histories.

CSV temperatures are in-situ ITS-90 (deg C), salinity is Practical Salinity,
current is east/north (m/s) and depth is metres positive down. Actual provider
meaning remains bound to its named forcing key; no thermodynamic conversion here.
"""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
from typing import Any, Mapping

from ..errors import ConfigError, ProviderDataError
from .base import ProviderContext, ProviderProvenance, ProviderResult
from .builtin import _format_datetime, _nonempty_string, _parse_timestamp, _portable_path, _reject_unknown


def _load_csv(spec: Mapping[str, Any], context: ProviderContext, *, columns: tuple[str, ...],
              vector: bool) -> ProviderResult:
    configured = Path(str(spec["path"]))
    path = (configured if configured.is_absolute() else context.config_dir / configured).resolve()
    if not path.is_file():
        raise ProviderDataError(f"historical CSV file does not exist: {path}")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    records: list[dict[str, Any]] = []
    previous: tuple[str, float] | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for column in columns:
            if column not in (reader.fieldnames or []):
                raise ProviderDataError(f"historical CSV {path} missing column {column!r}")
        for row_number, row in enumerate(reader, start=2):
            try:
                parsed = _parse_timestamp(row[str(spec["time_column"])])
                if parsed.microsecond:
                    raise ValueError("fractional timestamps are unsupported in TIME-1A's whole-second clock")
                when = _format_datetime(parsed)
                depth = float(row[str(spec["depth_column"])])
                if vector:
                    u = float(row[str(spec["u_column"])])
                    v = float(row[str(spec["v_column"])])
                    values = (u, v)
                else:
                    values = (float(row[str(spec["value_column"])]),)
            except (ValueError, TypeError, KeyError) as exc:
                raise ProviderDataError(f"historical CSV {path} row {row_number} has invalid time/depth/value") from exc
            if depth < 0 or not all(math.isfinite(val) for val in (depth, *values)):
                raise ProviderDataError(f"historical CSV {path} row {row_number} needs finite depth>=0 and values")
            # Compare *aware datetimes*, not strings: canonical UTC ISO is monotonic.
            if previous is not None and (when < previous[0] or
                                         (when == previous[0] and depth <= previous[1])):
                raise ProviderDataError(f"historical CSV {path} times/depths must be strictly ordered, without duplicates")
            previous = (when, depth)
            record: dict[str, Any] = {"time": when, "depth_m": depth}
            if vector:
                record.update({"u_east_mps": values[0], "v_north_mps": values[1]})
            else:
                record["value"] = values[0]
            records.append(record)
    if not records:
        raise ProviderDataError(f"historical CSV {path} is empty")
    return ProviderResult(
        data_kind="time_depth_vector" if vector else "time_depth_profile",
        records=tuple(records),
        provenance=ProviderProvenance(provider=str(spec["provider"]), source=str(path),
                                       request=dict(spec), input_sha256=digest),
    )


class CsvTimeDepthProfileProvider:
    """Time/depth scalar CSV; explicit UTC time, depth and named value columns."""

    name = "csv_time_depth_profile"

    def normalize_spec(self, raw: Mapping[str, Any], *, context: str) -> dict[str, Any]:
        _reject_unknown(raw, {"provider", "path", "time_column", "depth_column", "value_column"}, context)
        if "path" not in raw:
            raise ConfigError(f"{context}.path is required")
        return {"provider": self.name,
                "path": _portable_path(raw["path"], f"{context}.path"),
                "time_column": _nonempty_string(raw.get("time_column", "time"), context),
                "depth_column": _nonempty_string(raw.get("depth_column", "depth_m"), context),
                "value_column": _nonempty_string(raw.get("value_column", "value"), context)}

    def load(self, spec: Mapping[str, Any], *, context: ProviderContext) -> ProviderResult:
        return _load_csv(spec, context,
                         columns=(str(spec["time_column"]), str(spec["depth_column"]),
                                  str(spec["value_column"])), vector=False)


class CsvTimeVectorProfileProvider:
    """Time/depth current CSV in strictly local ENU east/north components."""

    name = "csv_time_vector_profile"

    def normalize_spec(self, raw: Mapping[str, Any], *, context: str) -> dict[str, Any]:
        _reject_unknown(raw, {"provider", "path", "time_column", "depth_column", "u_column", "v_column"}, context)
        if "path" not in raw:
            raise ConfigError(f"{context}.path is required")
        return {"provider": self.name,
                "path": _portable_path(raw["path"], f"{context}.path"),
                "time_column": _nonempty_string(raw.get("time_column", "time"), context),
                "depth_column": _nonempty_string(raw.get("depth_column", "depth_m"), context),
                "u_column": _nonempty_string(raw.get("u_column", "u_east_mps"), context),
                "v_column": _nonempty_string(raw.get("v_column", "v_north_mps"), context)}

    def load(self, spec: Mapping[str, Any], *, context: ProviderContext) -> ProviderResult:
        return _load_csv(spec, context,
                         columns=(str(spec["time_column"]), str(spec["depth_column"]),
                                  str(spec["u_column"]), str(spec["v_column"])), vector=True)
