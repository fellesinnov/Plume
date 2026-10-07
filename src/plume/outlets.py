"""Outlet config adapters.

CORE-0 owns geometry normalization only. A registered outlet here does not imply
that a plume-physics implementation exists for that outlet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .errors import ConfigError, UnsupportedOutletError


class OutletAdapter(Protocol):
    """Normalize one tagged outlet geometry into the product coordinate contract."""

    outlet_type: str

    def normalize(self, raw: Mapping[str, Any], *, water_depth_m: float) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SingleRoundPortAdapter:
    outlet_type: str = "single_round_port"

    def normalize(self, raw: Mapping[str, Any], *, water_depth_m: float) -> dict[str, Any]:
        allowed = {
            "type",
            "diameter_m",
            "discharge_depth_below_surface_m",
            "vertical_angle_deg",
            "azimuth_deg",
        }
        _reject_unknown(raw, allowed, "outfall")
        diameter = _number(raw, "diameter_m", "outfall")
        depth = _number(raw, "discharge_depth_below_surface_m", "outfall")
        vertical_angle = _number(raw, "vertical_angle_deg", "outfall")
        azimuth = _number(raw, "azimuth_deg", "outfall")

        if diameter <= 0:
            raise ConfigError("outfall.diameter_m must be > 0")
        if not 0 <= depth <= water_depth_m:
            raise ConfigError(
                "outfall.discharge_depth_below_surface_m must be between 0 and site.water_depth_m"
            )
        if not -90 <= vertical_angle <= 90:
            raise ConfigError("outfall.vertical_angle_deg must be between -90 and 90")
        if not 0 <= azimuth < 360:
            raise ConfigError("outfall.azimuth_deg must be in [0, 360)")

        return {
            "type": self.outlet_type,
            "diameter_m": diameter,
            "discharge_depth_below_surface_m": depth,
            "vertical_angle_deg": vertical_angle,
            "azimuth_deg": azimuth,
        }


def _number(raw: Mapping[str, Any], key: str, context: str) -> float:
    if key not in raw:
        raise ConfigError(f"{context}.{key} is required")
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{context}.{key} must be a number")
    return float(value)


def _reject_unknown(raw: Mapping[str, Any], allowed: set[str], context: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ConfigError(f"{context} has unsupported field(s): {', '.join(unknown)}")


_OUTLET_ADAPTERS: dict[str, OutletAdapter] = {
    SingleRoundPortAdapter.outlet_type: SingleRoundPortAdapter(),
}


def register_outlet_adapter(adapter: OutletAdapter) -> None:
    """Register an outlet config adapter explicitly."""

    if not adapter.outlet_type:
        raise ValueError("adapter.outlet_type must be non-empty")
    _OUTLET_ADAPTERS[adapter.outlet_type] = adapter


def normalize_outfall(raw: Mapping[str, Any], *, water_depth_m: float) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ConfigError("outfall must be a mapping")
    outlet_type = raw.get("type")
    if not isinstance(outlet_type, str) or not outlet_type:
        raise ConfigError("outfall.type must be a non-empty string")
    adapter = _OUTLET_ADAPTERS.get(outlet_type)
    if adapter is None:
        supported = ", ".join(sorted(_OUTLET_ADAPTERS))
        raise UnsupportedOutletError(
            f"unsupported outfall.type {outlet_type!r}; supported: {supported}"
        )
    return adapter.normalize(raw, water_depth_m=water_depth_m)


def supported_outlet_types() -> tuple[str, ...]:
    return tuple(sorted(_OUTLET_ADAPTERS))
