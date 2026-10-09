"""TIME-1B Copernicus Marine gridded history adapter (headless and fail-closed).

Only explicit temperature, Practical Salinity, and local ENU-current roles are
supported. Potential temperature is NOT passed through as in-situ ITS-90.
A bounded wet-cell search and vertical boundary policy are always disclosed.
All remote I/O happens on explicit history acquisition, never in model/UI code.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Mapping

import numpy as np

from ..errors import ConfigError, ProviderDataError
from .base import ProviderContext, ProviderProvenance, ProviderResult
from .builtin import _nonempty_string, _reject_unknown, _number, _parse_timestamp

_SUPPORTED_ROLES = {"temperature", "salinity", "current"}
_DEG_C = {"degrees_c", "degree_celsius", "degc", "celsius", "degree_c", "degrees_celsius"}
_M_S = {"m/s", "m s-1", "m s**-1", "m s^-1", "meter second-1", "metre second-1"}


def _haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    a, b = math.radians(lat_a), math.radians(lat_b)
    dlat, dlon = b-a, math.radians(lon_b-lon_a)
    h = math.sin(dlat/2)**2 + math.cos(a)*math.cos(b)*math.sin(dlon/2)**2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(max(0, h))))


def _timestamp(value: Any) -> str:
    try:
        if isinstance(value, np.datetime64):
            if np.isnat(value):
                raise ValueError("NaT")
            # Round-trip nanosecond timestamps, but explicitly reject any
            # non-whole-second measurement rather than alias to hourly clock.
            nanos = int(value.astype("datetime64[ns]").astype("int64"))
            if nanos % 1_000_000_000:
                raise ValueError("subsecond Copernicus timestamp")
            value = str(value.astype("datetime64[s]")) + "Z"
        dt = _parse_timestamp(str(value))
        if dt.microsecond:
            raise ValueError("subsecond timestamp")
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (ValueError, OverflowError, TypeError) as exc:
        raise ProviderDataError("Copernicus time coordinate must represent an exact UTC second") from exc


def _unit_units(var: Any) -> str:
    return str(var.attrs.get("units", "")).strip().lower().replace(" ", "_")


def _validate_units(var: Any, role: str) -> None:
    actual = _unit_units(var)
    accepted = _M_S if role == "current" else _DEG_C if role == "temperature" else {"1e-3", "0.001", "psu", "1"}
    # Do not accept missing temperature/current units: silent Kelvin or cm/s
    # relabeling would break buoyancy and trajectory predictions.
    if actual not in {s.replace(" ", "_") for s in accepted}:
        raise ProviderDataError(f"Copernicus {role} unit {actual!r} is not supported; require explicit verified units")


def _open_dataset(**kwargs: Any):
    """Isolated transport seam for injection in deterministic source tests."""
    try:
        import copernicusmarine
    except ImportError as exc:
        raise ProviderDataError("install Plume's ocean optional dependency: pip install -e '.[ocean]'") from exc
    return copernicusmarine.open_dataset(**kwargs)


def _data_matrix(dataset: Any, variable: str, lat_idx: int, lon_idx: int) -> np.ndarray:
    arr = dataset[variable].isel(latitude=lat_idx, longitude=lon_idx).transpose("time", "depth")
    values = np.asarray(arr.values, dtype=float)
    if values.ndim != 2:
        raise ProviderDataError("Copernicus variable must be time/depth/latitude/longitude gridded")
    return values


def _normalise_depth_profile(depths: np.ndarray, *series: np.ndarray,
                             seabed_m: float, surface_hold_limit_m: float) -> tuple[list[float], list[np.ndarray], bool]:
    """Explicitly bounded top-cell hold; interpolate ONLY within sampled depths at seabed."""
    if depths.ndim != 1 or len(depths) < 2 or not np.all(np.isfinite(depths)) or np.any(np.diff(depths) <= 0):
        raise ProviderDataError("Copernicus depths must be finite, strictly increasing, with two levels")
    if depths[0] < 0 or depths[0] > surface_hold_limit_m:
        raise ProviderDataError("Copernicus surface wet level too deep for requested surface proxy")
    if depths[-1] < seabed_m:
        raise ProviderDataError("Copernicus selected wet cell does not span configured seabed: no bottom extrapolation")
    if any(len(v) != len(depths) for v in series):
        raise ProviderDataError("Copernicus profile depth/value shape mismatch")
    used_depths = [0.0] + [float(d) for d in depths if 0 < d < seabed_m]
    if used_depths[-1] != seabed_m:
        used_depths.append(float(seabed_m))
    out = []
    for data in series:
        if not np.isfinite(data).all():
            raise ProviderDataError("Copernicus profile contains masked or missing vertical levels")
        out.append(np.interp(used_depths, depths, data, left=float(data[0])))
    return used_depths, out, bool(depths[0] > 0)


def _pick_wet_cell(ds: Any, names: tuple[str, ...], lat: float, lon: float, seabed: float,
                   max_dist: float, surface_limit: float) -> tuple[int, int, float]:
    lats = np.asarray(ds.latitude.values, dtype=float)
    lons = np.asarray(ds.longitude.values, dtype=float)
    if lats.ndim != 1 or lons.ndim != 1 or not len(lats) or not len(lons):
        raise ProviderDataError("Copernicus expects rectilinear latitude/longitude coordinates")
    depth = np.asarray(ds.depth.values, dtype=float)
    if depth.ndim != 1 or len(depth) < 2 or not np.isfinite(depth).all() or np.any(np.diff(depth) <= 0):
        raise ProviderDataError("Copernicus depth coordinates must be increasing and finite")
    if depth[-1] < seabed or depth[0] > surface_limit:
        raise ProviderDataError("Copernicus product cannot represent requested full water column")
    needed = int(np.searchsorted(depth, seabed, side="left")) + 1
    # Deep downloaded levels may be masked because a coastal cell is only
    # deep enough for the requested seabed, not the full query maximum.
    # Never require those irrelevant deeper levels to be wet.
    if len(lats) * len(lons) > 20000:
        raise ProviderDataError("Copernicus wet-cell search area too large; narrow search radius")
    candidates = sorted((( _haversine_km(lat, lon, float(y), float(x)), yi, xi)
                         for yi, y in enumerate(lats) for xi, x in enumerate(lons)), key=lambda v:v[0])
    for dist, yi, xi in candidates[:64]:
        if dist > max_dist:
            break
        arrays = [_data_matrix(ds, name, yi, xi)[:, :needed] for name in names]
        # At least ONE complete timestamp at the prospective cell. Others may
        # legitimately be missing hours, which are recorded as explicit gaps.
        if all(a.shape == (len(ds.time), needed) for a in arrays):
            valid = np.ones(len(ds.time), dtype=bool)
            for a in arrays:
                valid &= np.all(np.isfinite(a), axis=1)
            if np.any(valid):
                return yi, xi, dist
    raise ProviderDataError("No full-depth wet Copernicus cell within configured fallback distance")


class CopernicusProvider:
    """One role per descriptor, request scoped by ProviderContext site/clock."""
    name = "copernicus"

    def normalize_spec(self, raw: Mapping[str, Any], *, context: str) -> dict[str, Any]:
        allowed = {"provider", "role", "dataset_id", "variable", "salinity_variable", "u_variable",
                   "v_variable", "temperature_kind", "search_radius_deg", "max_fallback_km",
                   "surface_proxy_limit_m", "dataset_version", "salinity_kind"}
        _reject_unknown(raw, allowed, context)
        role = _nonempty_string(raw.get("role"), f"{context}.role")
        if role not in _SUPPORTED_ROLES:
            raise ConfigError(f"{context}.role must be one of {sorted(_SUPPORTED_ROLES)}")
        expected = ("temperature" if context.endswith("temperature_profile_C") else
                    "salinity" if context.endswith("salinity_profile_psu") else
                    "current" if context.endswith("current_profile") else None)
        if expected is not None and role != expected:
            raise ConfigError(f"{context}: Copernicus role {role} must match {expected}")
        role_only = ({"temperature": {"u_variable", "v_variable"},
                      "salinity": {"temperature_kind", "salinity_variable", "u_variable", "v_variable"},
                      "current": {"variable", "temperature_kind", "salinity_kind", "salinity_variable"}}[role])
        if set(raw) & role_only:
            raise ConfigError(f"{context}: incompatible Copernicus {role} options: {sorted(set(raw) & role_only)}")
        out: dict[str, Any] = {"provider": self.name, "role": role,
                               "dataset_id": _nonempty_string(raw.get("dataset_id"), context)}
        if role == "current":
            out["u_variable"] = _nonempty_string(raw.get("u_variable", "uo"), context)
            out["v_variable"] = _nonempty_string(raw.get("v_variable", "vo"), context)
        else:
            out["variable"] = _nonempty_string(raw.get("variable", "thetao" if role == "temperature" else "so"), context)
        if role == "temperature":
            kind = raw.get("temperature_kind")
            if kind not in {"in_situ_ITS90", "potential_pt0"}:
                raise ConfigError("Copernicus temperature_kind must explicitly be in_situ_ITS90 or potential_pt0")
            out["temperature_kind"] = kind
            if kind == "in_situ_ITS90" and any(
                key in raw for key in ("salinity_kind", "salinity_variable")
            ):
                raise ConfigError("in_situ_ITS90 cannot use ignored salinity conversion options")
            if kind == "potential_pt0":
                if raw.get("salinity_kind") != "practical":
                    raise ConfigError("potential_pt0 needs explicit salinity_kind: practical for companion so")
                out["salinity_kind"] = "practical"
                # Some Copernicus history products split thetao and so into
                # separate dataset IDs. With no companion in this dataset,
                # defer the conversion until TIME-1A pairs the exact-hour SP.
                if "salinity_variable" in raw:
                    out["salinity_variable"] = _nonempty_string(raw["salinity_variable"], context)
        if role == "salinity":
            if raw.get("salinity_kind") != "practical":
                raise ConfigError("Copernicus salinity requires explicit salinity_kind: practical")
            out["salinity_kind"] = "practical"
        for key, default, minimum, maximum in (
            ("search_radius_deg", .10, .005, 2.0),
            ("max_fallback_km", 8., 0., 50.),
            ("surface_proxy_limit_m", 1.1, 0., 2.0),
        ):
            value = _number(raw.get(key, default), context)
            if not math.isfinite(value) or not minimum <= value <= maximum:
                raise ConfigError(f"Copernicus {key} must be in [{minimum}, {maximum}]")
            out[key] = value
        if "dataset_version" in raw:
            out["dataset_version"] = _nonempty_string(raw["dataset_version"], context)
        return out

    def load(self, spec: Mapping[str, Any], *, context: ProviderContext) -> ProviderResult:
        site, clock = context.site, context.clock
        if site is None or clock is None:
            raise ProviderDataError("Copernicus historical provider requires explicit site and UTC forcing clock")
        role = str(spec["role"])
        requested_lat, requested_lon = float(site["latitude_deg"]), float(site["longitude_deg"])
        seabed = float(site["water_depth_m"])
        margin = float(spec["search_radius_deg"])
        if requested_lon-margin < -180 or requested_lon+margin > 180:
            raise ProviderDataError("Copernicus antimeridian crossing needs a separate split request")
        start = _parse_timestamp(str(clock["start"]))
        end = _parse_timestamp(str(clock["end"]))
        if end <= start:
            raise ProviderDataError("Copernicus request clock must have positive duration")
        names = ((spec["u_variable"], spec["v_variable"]) if role == "current" else
                 (spec["variable"], spec["salinity_variable"]) if role == "temperature" and "salinity_variable" in spec else
                 (spec["variable"],))
        names = tuple(dict.fromkeys(names))
        # Site/cadence/selection/variables belong to history request SHA; no
        # credentials or tokens are stored in provider descriptors or logs.
        kwargs = {
            "dataset_id": str(spec["dataset_id"]), "variables": list(names),
            "minimum_longitude": requested_lon-margin,
            "maximum_longitude": requested_lon+margin,
            "minimum_latitude": max(-90., requested_lat-margin),
            "maximum_latitude": min(90., requested_lat+margin),
            "minimum_depth": 0., "maximum_depth": max(seabed+10, 1.5*seabed),
            "start_datetime": start.isoformat(timespec="seconds"),
            "end_datetime": end.isoformat(timespec="seconds"),
        }
        if "dataset_version" in spec:
            kwargs["dataset_version"] = spec["dataset_version"]
        try:
            ds = _open_dataset(**kwargs)
            if "lat" in ds.coords and "latitude" not in ds.coords:
                ds = ds.rename({"lat": "latitude"})
            if "lon" in ds.coords and "longitude" not in ds.coords:
                ds = ds.rename({"lon": "longitude"})
            for coord in ("time", "depth", "latitude", "longitude"):
                if coord not in ds.coords:
                    raise ProviderDataError(f"Copernicus gridded data missing {coord} coordinate")
            for name in names:
                if name not in ds.data_vars:
                    raise ProviderDataError(f"Copernicus dataset missing variable {name!r}")
                _validate_units(ds[name], "current" if role == "current" else "temperature" if name == spec.get("variable") and role == "temperature" else "salinity")
            for sal_var in (names if role == "salinity" else (spec["salinity_variable"],) if role == "temperature" and "salinity_variable" in spec else ()):
                std_s = str(ds[sal_var].attrs.get("standard_name", ""))
                if std_s in {"sea_water_absolute_salinity", "sea_water_reference_salinity"}:
                    raise ProviderDataError("Copernicus salinity metadata is not Practical Salinity")
            if role == "temperature":
                std = str(ds[spec["variable"]].attrs.get("standard_name", ""))
                if spec["temperature_kind"] == "potential_pt0":
                    if std != "sea_water_potential_temperature":
                        raise ProviderDataError("potential_pt0 requested but thetao metadata is not sea_water_potential_temperature")
                elif std not in {"sea_water_temperature", "sea_water_in_situ_temperature"}:
                    # An explicit config knob cannot override conflicting
                    # dataset quantity metadata; avoid treating pt0 as in-situ.
                    raise ProviderDataError("in_situ_ITS90 requested but native temperature metadata is not in-situ")
            yi, xi, dist = _pick_wet_cell(ds, names, requested_lat, requested_lon, seabed,
                                          float(spec["max_fallback_km"]), float(spec["surface_proxy_limit_m"]))
            used_lat, used_lon = float(ds.latitude.values[yi]), float(ds.longitude.values[xi])
            full_depths = np.asarray(ds.depth.values, dtype=float)
            needed = int(np.searchsorted(full_depths, seabed, side="left")) + 1
            depths = full_depths[:needed]
            matrices = {name: _data_matrix(ds, name, yi, xi)[:, :needed] for name in names}
            times = [_timestamp(t) for t in np.asarray(ds.time.values)]
            if len(set(times)) != len(times) or any(b <= a for a,b in zip(times, times[1:])):
                raise ProviderDataError("Copernicus native timestamps are unordered or repeated")
            records: list[dict[str, Any]] = []
            had_surface_hold = False
            missed = 0
            for idx, stamp in enumerate(times):
                current_time = _parse_timestamp(stamp)
                if not start <= current_time < end:
                    continue
                arrays = [matrices[name][idx] for name in names]
                if not all(np.all(np.isfinite(a)) for a in arrays):
                    missed += 1
                    continue
                targets, normalized, surface_hold = _normalise_depth_profile(
                    depths, *arrays, seabed_m=seabed,
                    surface_hold_limit_m=float(spec["surface_proxy_limit_m"]))
                had_surface_hold |= surface_hold
                if role == "temperature":
                    temps = normalized[0]
                    if spec["temperature_kind"] == "potential_pt0" and "salinity_variable" in spec:
                        try:
                            import gsw
                        except ImportError as exc:
                            raise ProviderDataError("GSW required for potential-temperature conversion") from exc
                        practical = normalized[1]
                        sea_p = gsw.p_from_z(-np.asarray(targets), used_lat)
                        abs_s = gsw.SA_from_SP(practical, sea_p, used_lon, used_lat)
                        conservative = gsw.CT_from_pt(abs_s, temps)
                        temps = gsw.t_from_CT(abs_s, conservative, sea_p)
                    pairs = zip(targets, np.asarray(temps, dtype=float))
                elif role == "salinity":
                    if np.any(normalized[0] < 0):
                        raise ProviderDataError("Copernicus Practical Salinity cannot be negative")
                    pairs = zip(targets, normalized[0])
                else:
                    pairs = zip(targets, normalized[0], normalized[1])
                for values in pairs:
                    d, *v = (float(x) for x in values)
                    if not all(math.isfinite(x) for x in v):
                        raise ProviderDataError("Copernicus converted forcing contains nonfinite values")
                    if role == "current":
                        records.append({"time": stamp, "depth_m": d, "u_east_mps": v[0], "v_north_mps": v[1]})
                    else:
                        records.append({"time": stamp, "depth_m": d, "value": v[0]})
            if not records:
                raise ProviderDataError("Copernicus request has no usable full-depth time profiles")
            notes: list[str] = []
            if dist > .001:
                notes.append(f"Requested ({requested_lat:.6f},{requested_lon:.6f}); selected wet cell ({used_lat:.6f},{used_lon:.6f}), {dist:.3f} km away")
            if had_surface_hold:
                notes.append(f"Top wet level at {float(depths[0]):g}m represented as surface [0m] by a clearly labelled bounded hold, NOT measured at 0m")
            if missed:
                notes.append(f"{missed} native timestamps masked/incomplete; skipped, not interpolated")
            native = {"normalized_spec": dict(spec), "dataset_id": str(spec["dataset_id"]),
                      "actual_latitude_deg": used_lat, "actual_longitude_deg": used_lon,
                      "requested_latitude_deg": requested_lat, "requested_longitude_deg": requested_lon,
                      "cell_fallback_km": dist, "native_levels_m": depths.tolist(),
                      "downloaded_native_levels_m": full_depths.tolist(),
                      "surface_proxy_method": "top_wet_value_held_to_zero" if had_surface_hold else "native_surface_zero",
                      "bottom_method": "bounded_linear_vertical_interpolation_no_extrapolation",
                      "conversion": ("potential_pt0_to_in_situ_ITS90_via_GSW" if role == "temperature" and
                                     spec["temperature_kind"] == "potential_pt0" and "salinity_variable" in spec else
                                     "DEFERRED_potential_pt0_to_in_situ_with_paired_history_SP" if role == "temperature" and
                                     spec["temperature_kind"] == "potential_pt0" else "no_thermodynamic_conversion"),
                      "variables": list(names), "dataset_attrs": {key: str(ds.attrs[key])[:300]
                                                              for key in ("title", "cmems_product_id", "Conventions", "dataset_version") if key in ds.attrs}}
            encoded = json.dumps(records, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            result_kind = ("time_depth_vector" if role == "current" else
                           "time_depth_potential" if role == "temperature" and
                           spec["temperature_kind"] == "potential_pt0" and "salinity_variable" not in spec
                           else "time_depth_profile")
            result = ProviderResult(data_kind=result_kind,
                records=tuple(records), provenance=ProviderProvenance(
                    provider=self.name, source=str(spec["dataset_id"]), request=native,
                    input_sha256=hashlib.sha256(encoded).hexdigest(), warnings=tuple(notes)))
            return result
        except ProviderDataError:
            raise
        except Exception as exc:
            # Avoid logging transport exception text, which may contain a URL
            # with user authentication material from an upstream client.
            raise ProviderDataError("Copernicus dataset query failed; check account, dataset, location and time availability") from exc
        finally:
            if "ds" in locals() and hasattr(ds, "close"):
                ds.close()
