"""TIME-1A local historical forcing, content-addressed acquisition, exact UTC selection.

No Streamlit, Copernicus, model solver or reference fixture imports. The
DESIGN-1 pinned snapshot is the sole bridge to later MODEL/FIELD replay.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from ..config import LoadedConfig
from ..design.snapshot import PinnedSnapshot, _digest, _profile, _scalar, _timestamp
from ..errors import ProviderDataError
from ..providers import ProviderContext, ProviderProvenance, ProviderResult, load_provider
from ..providers.builtin import _parse_timestamp
from ..workspace import resolve_workspace_root

_SCHEMA = 1
_STEP = re.compile(r"^P(?:(?P<days>\d+(?:\.\d+)?)D)?(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?(?:(?P<minutes>\d+(?:\.\d+)?)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$")
_SOURCE_ALLOWED = {"flow_m3h", "delta_T_C", "discharge_temperature_C", "salinity_psu"}
_AMBIENT_EXPECTED = {"temperature_profile_C", "salinity_profile_psu", "current_profile"}
_LOCAL_FILES = {"csv", "csv_depth_profile", "csv_time_depth_profile", "csv_time_vector_profile"}


def _clock_times(clock: Mapping[str, Any]) -> tuple[str, ...]:
    start = _parse_timestamp(str(clock["start"]))
    end = _parse_timestamp(str(clock["end"]))
    if start.microsecond or end.microsecond:
        raise ProviderDataError("TIME-1A requires whole-second UTC clock boundaries; subsecond clock endpoints are unsupported")
    match = _STEP.fullmatch(str(clock["step"]))
    if match is None:
        raise ProviderDataError("historical clock step is not an ISO-8601 day/time duration")
    step_seconds = sum(float(match.group(key) or 0) * factor for key, factor in
                       (("days", 86400), ("hours", 3600), ("minutes", 60), ("seconds", 1)))
    if not step_seconds.is_integer() or step_seconds < 1:
        raise ProviderDataError("TIME-1A requires whole-second positive clock steps")
    delta = timedelta(seconds=int(step_seconds))
    count = math.ceil((end - start).total_seconds() / step_seconds)
    if count < 1 or count > 100000:
        raise ProviderDataError("historical clock must have 1..100000 steps")
    return tuple((start + i * delta).isoformat(timespec="seconds").replace("+00:00", "Z")
                 for i in range(count))


def _request_payload(config: LoadedConfig) -> dict[str, Any]:
    """Key ocean/plant/time/location and the raw bytes of local files, never geometry.

    No remote provider is contacted while computing a request key. Future
    Copernicus adapters should supply stable normalized dataset/request IDs.
    """
    normalized = config.normalized
    force = normalized["forcing"]
    source, ambient = force["source"], force["ambient"]
    if not ("flow_m3h" in source and ("delta_T_C" in source) != ("discharge_temperature_C" in source)
            and not set(source) - _SOURCE_ALLOWED and set(ambient) == _AMBIENT_EXPECTED):
        raise ProviderDataError("history requires source flow + one temperature definition and full T/SP/current ambient")
    files: dict[str, dict[str, str]] = {}
    for group, specs in (("source", source), ("ambient", ambient)):
        for key, spec in sorted(specs.items()):
            if spec["provider"] in _LOCAL_FILES:
                named = Path(str(spec["path"]))
                absolute = (named if named.is_absolute() else config.source_dir / named).resolve()
                if not absolute.is_file():
                    raise ProviderDataError(f"local historical source missing: {absolute}")
                files[f"{group}.{key}"] = {
                    "resolved_path": str(absolute),
                    "sha256": hashlib.sha256(absolute.read_bytes()).hexdigest(),
                }
    return {"schema_version": _SCHEMA, "site": copy.deepcopy(normalized["site"]),
            "clock": copy.deepcopy(force["clock"]),
            "source": copy.deepcopy(source), "ambient": copy.deepcopy(ambient),
            "local_input_files": files}


def _validate_profile(rows: tuple[Mapping[str, Any], ...], *, name: str,
                      depth_m: float) -> None:
    # Existing DESIGN-1 normalized-profile boundary (surface + seabed,
    # strictly increasing depth, finite values, no extrapolation).
    result = ProviderResult(data_kind="depth_profile", records=rows,
                            provenance=ProviderProvenance(provider="history", source="cached", request={}))
    _profile(result, name, depth_m)


def _select_records(item: Mapping[str, Any], timestamp: str) -> tuple[Mapping[str, Any], ...]:
    kind = str(item["data_kind"])
    if kind in {"time_depth_profile", "time_depth_potential", "time_depth_vector", "scalar_time_series"}:
        return tuple(item["records_by_time"].get(timestamp, ()))  # O(1) slot lookup, not annual scan
    return tuple(item["records"])


def _check_sample(item: Mapping[str, Any], key: str, at: str, water_depth: float) -> bool:
    kind = str(item["data_kind"])
    if key in {"ambient.temperature_profile_C", "ambient.salinity_profile_psu"}:
        supported = ({"depth_profile", "time_depth_profile", "time_depth_potential"}
                     if key == "ambient.temperature_profile_C" else
                     {"depth_profile", "time_depth_profile"})
    elif key == "ambient.current_profile":
        supported = {"vector_constant", "time_depth_vector"}
    else:
        supported = {"scalar", "scalar_time_series"}
    if kind not in supported:
        raise ProviderDataError(f"{key}: wrong historical provider shape {kind!r}; expected {sorted(supported)}")
    selected = _select_records(item, at)
    if kind in {"depth_profile", "time_depth_profile", "time_depth_potential"}:
        if not selected:
            return False
        _validate_profile(tuple({"depth_m": row["depth_m"], "value": row["value"]}
                                for row in selected), name=key.split(".")[-1], depth_m=water_depth)
    elif kind == "vector_constant":
        if len(selected) != 1:
            raise ProviderDataError("vector_constant requires one current vector")
        if not all(math.isfinite(float(selected[0][c])) for c in ("u_east_mps", "v_north_mps")):
            raise ProviderDataError("current vector must be finite")
    elif kind == "time_depth_vector":
        if not selected:
            return False
        depths = [float(row["depth_m"]) for row in selected]
        if (len(depths) < 2 or abs(depths[0]) > 1e-8 or
                abs(depths[-1] - water_depth) > 1e-8 or
                any(b <= a for a, b in zip(depths, depths[1:])) or
                any(not math.isfinite(v) for row in selected
                    for v in (float(row["depth_m"]), float(row["u_east_mps"]), float(row["v_north_mps"])))):
            raise ProviderDataError(f"{key}: depth-vector profile must cover surface and bottom with finite increasing depths")
    elif kind in {"scalar", "scalar_time_series"}:
        if not selected:
            return False
        if len(selected) != 1:
            raise ProviderDataError(f"{key}: exactly one scalar value required at each timestamp")
        _scalar(ProviderResult(data_kind=kind, records=selected,
                               provenance=ProviderProvenance(provider="history", source="cached", request={})),
                key, at)
    else:
        raise ProviderDataError(f"{key}: unsupported historical provider result kind {kind!r}")
    return True


def _series_as_record(result: ProviderResult) -> dict[str, Any]:
    item: dict[str, Any] = {"data_kind": result.data_kind,
                            "provenance": result.manifest_summary()}
    if result.data_kind in {"time_depth_profile", "time_depth_potential", "time_depth_vector", "scalar_time_series"}:
        by_time: dict[str, list[dict[str, Any]]] = {}
        for record in result.records:
            by_time.setdefault(str(record["time"]), []).append(dict(record))
        item["records_by_time"] = by_time
    else:
        item["records"] = [dict(r) for r in result.records]
    return item


@dataclass(frozen=True)
class HistoricalForcing:
    """A provider-normalized history; data is pinned, solver/UI independent.

    The exact original descriptors (including source plant time series) live in
    the request and every selected snapshot. No source is silently replaced by
    DESIGN-1's one-hour constant design controls.
    """

    request: dict[str, Any]
    request_sha256: str
    series: dict[str, dict[str, Any]]
    clock_times: tuple[str, ...]
    available_times: tuple[str, ...]
    missing_by_time: dict[str, tuple[str, ...]]
    data_sha256: str
    cache_path: Path | None = field(default=None, compare=False)
    cache_hit: bool = field(default=False, compare=False)
    # The snapshot iterator must not scan the annual timestamp tuple for every
    # hour; the indexes are derived/rebuilt from SHA-bound serialized columns.
    _clock_index: frozenset[str] = field(init=False, repr=False, compare=False)
    _available_index: frozenset[str] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_clock_index", frozenset(self.clock_times))
        object.__setattr__(self, "_available_index", frozenset(self.available_times))

    def payload(self) -> dict[str, Any]:
        return {"format_version": _SCHEMA, "request": self.request,
                "request_sha256": self.request_sha256, "series": self.series,
                "clock_times": list(self.clock_times),
                "available_times": list(self.available_times),
                "missing_by_time": {k: list(v) for k, v in self.missing_by_time.items()}}

    def verify_identity(self) -> None:
        if _digest(self.request) != self.request_sha256 or _digest(self.payload()) != self.data_sha256:
            raise ProviderDataError("history data/request identity mismatch; reacquire history")

    def as_record(self) -> dict[str, Any]:
        self.verify_identity()
        return {**self.payload(), "data_sha256": self.data_sha256}

    @classmethod
    def from_record(cls, record: Mapping[str, Any], *, path: Path | None = None) -> "HistoricalForcing":
        try:
            if record["format_version"] != _SCHEMA:
                raise ProviderDataError("unknown local history cache format")
            actual = {k: record[k] for k in ("format_version", "request", "request_sha256",
                       "series", "clock_times", "available_times", "missing_by_time")}
            if _digest(actual["request"]) != actual["request_sha256"] or _digest(actual) != record["data_sha256"]:
                raise ProviderDataError("local history cache content digest mismatch")
            history = cls(request=copy.deepcopy(actual["request"]),
                          request_sha256=str(actual["request_sha256"]),
                          series=copy.deepcopy(actual["series"]),
                          clock_times=tuple(actual["clock_times"]),
                          available_times=tuple(actual["available_times"]),
                          missing_by_time={k: tuple(v) for k, v in actual["missing_by_time"].items()},
                          data_sha256=str(record["data_sha256"]), cache_path=path,
                          cache_hit=path is not None)
            if history.clock_times != _clock_times(history.request["clock"]):
                raise ProviderDataError("history cache clock/time identity mismatch")
            if ((set(history.available_times) | set(history.missing_by_time)) != set(history.clock_times)
                    or bool(set(history.available_times) & set(history.missing_by_time))):
                raise ProviderDataError("history cache availability inconsistent with requested clock")
            return history
        except ProviderDataError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderDataError("invalid history cache record") from exc

    def _require_config(self, config: LoadedConfig) -> None:
        normalized = config.normalized
        for field, current in (("site", normalized["site"]),
                               ("clock", normalized["forcing"]["clock"]),
                               ("source", normalized["forcing"]["source"]),
                               ("ambient", normalized["forcing"]["ambient"])):
            if current != self.request[field]:
                raise ProviderDataError(f"historical {field} changed; reacquire original forcing (do not reuse locked design constants)")

    def snapshot_at(self, config: LoadedConfig, at_utc: str) -> PinnedSnapshot:
        """Select exact timestamp from cached history, no provider I/O/interpolation."""
        self.verify_identity()
        self._require_config(config)
        return self._snapshot_unchecked(_timestamp(at_utc))

    def _snapshot_unchecked(self, when: str) -> PinnedSnapshot:
        """Internal O(levels) sampler for an already-verified history frame."""
        if when not in self._clock_index:
            raise ProviderDataError(f"historical timestamp {when} is outside selected clock grid")
        if when not in self._available_index:
            missing = self.missing_by_time.get(when, ())
            raise ProviderDataError(f"historical timestamp {when} has missing forcing: {', '.join(missing)}")
        temp_item = self.series["ambient.temperature_profile_C"]
        salt_item = self.series["ambient.salinity_profile_psu"]
        cur_item = self.series["ambient.current_profile"]
        temp = tuple((float(r["depth_m"]), float(r["value"])) for r in _select_records(temp_item, when))
        salt = tuple((float(r["depth_m"]), float(r["value"])) for r in _select_records(salt_item, when))
        potential_paired = temp_item["data_kind"] == "time_depth_potential"
        if potential_paired:
            from .temperature import paired_pt0_to_insitu
            actual = temp_item["provenance"]["request"]
            temp = paired_pt0_to_insitu(
                temp, salt,
                latitude_deg=float(actual["actual_latitude_deg"]),
                longitude_deg=float(actual["actual_longitude_deg"]),
            )
        selected = _select_records(cur_item, when)
        profile = None
        if cur_item["data_kind"] == "time_depth_vector":
            profile = [[float(r["depth_m"]), float(r["u_east_mps"]), float(r["v_north_mps"])]
                       for r in selected]
            current = [profile[0][1], profile[0][2]]  # surface representation only; profile drives solver
        else:
            current = [float(selected[0]["u_east_mps"]), float(selected[0]["v_north_mps"])]
        scalars: dict[str, float] = {}
        for key in self.request["source"]:
            item = self.series[f"source.{key}"]
            subset = _select_records(item, when)
            scalars[key] = float(subset[0]["value"])
        payload: dict[str, Any] = {
            "at_utc": when, "site": copy.deepcopy(self.request["site"]),
            "ambient_spec_sha256": _digest(self.request["ambient"]),
            "source_specs": copy.deepcopy(self.request["source"]),
            "temperature_profile_C": [list(r) for r in temp],
            "salinity_profile_psu": [list(r) for r in salt],
            "current_east_north_mps": current,
            "source_scalars": scalars,
            "providers": {f"forcing.{key}": copy.deepcopy(value["provenance"])
                          for key, value in self.series.items()},
        }
        if potential_paired:
            payload["providers"]["forcing.ambient.temperature_profile_C"]["request"][
                "selected_snapshot_temperature_conversion"
            ] = "paired_SP_at_same_UTC_and_depth_via_GSW_pt0_to_in_situ_ITS90"
        if profile is not None:
            payload["current_profile_east_north_mps"] = profile
        return PinnedSnapshot.from_record({**payload, "snapshot_sha256": _digest(payload)})

    def iter_available(self, config: LoadedConfig):
        """O(available timestamps × levels); integrity is checked once.

        Yields pinned inputs, not solver/permit outputs. Missing timestamps
        are exposed separately by missing_by_time, never interpolated.
        """
        self.verify_identity()
        self._require_config(config)
        for timestamp in self.available_times:
            yield self._snapshot_unchecked(timestamp)


def acquire_history(config: LoadedConfig, *, workspace_override: str | Path | None = None,
                    refresh: bool = False) -> HistoricalForcing:
    """Load all providers once, then persist/reuse an integrity-checked local cache.

    The workspace is ignored by Git. Source file contents are digested before
    cache lookup to avoid stale cache hits when a CSV is edited in place. No
    Copernicus credential/network interaction exists in this sprint.
    """
    request = _request_payload(config)
    request_sha = _digest(request)
    root = resolve_workspace_root(config, workspace_override)
    shared = config.normalized["workspace"]["shared_provider_cache"]
    folder = (root / "_cache" / "providers" / "history" if shared else
              root / "projects" / config.project_id / "_cache" / "history")
    path = folder / (request_sha + ".json")
    if path.is_file() and not refresh:
        try:
            decoded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ProviderDataError(f"history cache is corrupt: {path}") from exc
        cached = HistoricalForcing.from_record(decoded, path=path)
        if cached.request != request:
            raise ProviderDataError("history cache request does not match normalized source")
        return cached

    context = ProviderContext(config_dir=config.source_dir,
                              site=request["site"], clock=request["clock"])
    series: dict[str, dict[str, Any]] = {}
    for group in ("source", "ambient"):
        for key, spec in sorted(request[group].items()):
            result = load_provider(spec, context=context)
            name = f"{group}.{key}"
            local = request["local_input_files"].get(name)
            if local is not None and result.provenance.input_sha256 != local["sha256"]:
                raise ProviderDataError(f"{name}: source file changed during historical acquisition; retry")
            series[name] = _series_as_record(result)
    # A modeled vertical profile cannot silently combine widely separated
    # coastal grid cells. All Copernicus physical quantities must use mutually
    # coherent actual wet-cell coordinates, not just the user's point.
    actual_cells = [(name, float(item["provenance"]["request"]["actual_latitude_deg"]),
                     float(item["provenance"]["request"]["actual_longitude_deg"]))
                    for name, item in series.items()
                    if name.startswith("ambient.") and item["provenance"]["provider"] == "copernicus"]
    if len(actual_cells) > 1:
        from ..providers.copernicus import _haversine_km
        for i, (key_a, lat_a, lon_a) in enumerate(actual_cells):
            for key_b, lat_b, lon_b in actual_cells[i+1:]:
                if _haversine_km(lat_a, lon_a, lat_b, lon_b) > 2.0:
                    raise ProviderDataError(f"Copernicus wet cells for {key_a} and {key_b} differ by >2 km; do not merge as one water column")
    required = set(f"source.{key}" for key in request["source"]) | set(
        f"ambient.{key}" for key in request["ambient"])
    if set(series) != required:
        raise ProviderDataError("historical provider result missing mandatory forcing")
    times = _clock_times(request["clock"])
    water_depth = float(request["site"]["water_depth_m"])
    available: list[str] = []
    missing: dict[str, tuple[str, ...]] = {}
    for when in times:
        absent = tuple(key for key, item in sorted(series.items())
                       if not _check_sample(item, key, when, water_depth))
        if absent:
            missing[when] = absent
        else:
            available.append(when)
    if not available:
        raise ProviderDataError("no fully sampled historical forcing timestamps in selected clock")
    payload = {"format_version": _SCHEMA, "request": request,
               "request_sha256": request_sha, "series": series,
               "clock_times": list(times), "available_times": available,
               "missing_by_time": {k: list(v) for k, v in missing.items()}}
    history = HistoricalForcing.from_record({**payload, "data_sha256": _digest(payload)})
    folder.mkdir(parents=True, exist_ok=True)
    import uuid
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(history.as_record(), sort_keys=True,
                                        separators=(",", ":"), ensure_ascii=False) + "\n",
                             encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return replace(HistoricalForcing.from_record(history.as_record(), path=path), cache_hit=False)
