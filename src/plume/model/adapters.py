"""Physics adapters from normalized outlet config into MODEL-1 domain objects.

CORE-0's structural outlet registry answers whether a geometry can be
represented.  This module separately answers whether MODEL-1 has a physics
adapter for that normalized geometry, so future representable-but-unqualified
outlets fail explicitly rather than being approximated as a round port.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping, Protocol

from ..errors import ModelInputError, UnsupportedModelOutletError
from .nearfield import SingleRoundPort


class NearFieldOutletAdapter(Protocol):
    outlet_type: str

    def build(self, normalized: Mapping[str, Any]) -> SingleRoundPort: ...


@dataclass(frozen=True, slots=True)
class SingleRoundPortNearFieldAdapter:
    outlet_type: ClassVar[str] = "single_round_port"

    def build(self, normalized: Mapping[str, Any]) -> SingleRoundPort:
        if normalized.get("type") != self.outlet_type:
            raise ModelInputError(
                f"expected normalized outfall.type {self.outlet_type!r}, "
                f"got {normalized.get('type')!r}"
            )
        try:
            return SingleRoundPort(
                diameter_m=float(normalized["diameter_m"]),
                discharge_depth_below_surface_m=float(
                    normalized["discharge_depth_below_surface_m"]
                ),
                vertical_angle_deg=float(normalized["vertical_angle_deg"]),
                azimuth_deg=float(normalized["azimuth_deg"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelInputError(
                "normalized single_round_port outfall is missing valid geometry fields"
            ) from exc


_MODEL_OUTLET_ADAPTERS: dict[str, NearFieldOutletAdapter] = {
    SingleRoundPortNearFieldAdapter.outlet_type: SingleRoundPortNearFieldAdapter(),
}


def build_near_field_port(normalized_outfall: Mapping[str, Any]) -> SingleRoundPort:
    outlet_type = normalized_outfall.get("type")
    if not isinstance(outlet_type, str) or not outlet_type:
        raise ModelInputError("normalized outfall.type must be a non-empty string")
    adapter = _MODEL_OUTLET_ADAPTERS.get(outlet_type)
    if adapter is None:
        supported = ", ".join(sorted(_MODEL_OUTLET_ADAPTERS))
        raise UnsupportedModelOutletError(
            f"no MODEL-1 near-field adapter for outfall.type {outlet_type!r}; "
            f"supported: {supported}"
        )
    return adapter.build(normalized_outfall)


def supported_near_field_outlet_types() -> tuple[str, ...]:
    return tuple(sorted(_MODEL_OUTLET_ADAPTERS))
