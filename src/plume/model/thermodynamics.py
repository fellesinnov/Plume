"""Thermodynamic normalization and density contract for the near-field kernel.

The production path uses TEOS-10 through the official ``gsw`` package.  The
near-field solver itself only consumes Absolute Salinity and Conservative
Temperature; provider/user quantities are converted before they enter the
conservation equations.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Protocol

from ..errors import ModelInputError, ThermodynamicsError


@dataclass(frozen=True, slots=True)
class SeawaterState:
    """Thermodynamic state transported by the production near-field kernel."""

    absolute_salinity_gkg: float
    conservative_temperature_C: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.absolute_salinity_gkg):
            raise ModelInputError("absolute_salinity_gkg must be finite")
        if not math.isfinite(self.conservative_temperature_C):
            raise ModelInputError("conservative_temperature_C must be finite")
        if self.absolute_salinity_gkg < 0.0:
            raise ModelInputError("absolute_salinity_gkg must be >= 0")


class Thermodynamics(Protocol):
    """Minimal pressure-aware thermodynamic service required by MODEL-1."""

    def pressure_dbar(self, depth_m: float, latitude_deg: float) -> float: ...

    def density_kg_m3(
        self,
        state: SeawaterState,
        *,
        depth_m: float,
        latitude_deg: float,
    ) -> float: ...

    def in_situ_temperature_C(
        self,
        state: SeawaterState,
        *,
        depth_m: float,
        latitude_deg: float,
    ) -> float: ...


class GswThermodynamics:
    """TEOS-10 implementation backed by the official GSW-Python package.

    Import is lazy so deterministic kernel tests can inject a small test double
    without silently falling back to an obsolete seawater equation of state.
    """

    def __init__(self, gsw_module: Any | None = None) -> None:
        if gsw_module is None:
            try:
                import gsw as gsw_module  # type: ignore[no-redef]
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise ThermodynamicsError(
                    "TEOS-10 requires the 'gsw' package; install plume-engine model dependencies"
                ) from exc
        self._gsw = gsw_module

    def pressure_dbar(self, depth_m: float, latitude_deg: float) -> float:
        if depth_m < 0.0:
            raise ModelInputError("depth_m must be >= 0")
        return float(self._gsw.p_from_z(-float(depth_m), float(latitude_deg)))

    def from_practical_salinity_in_situ(
        self,
        *,
        practical_salinity: float,
        in_situ_temperature_C: float,
        depth_m: float,
        latitude_deg: float,
        longitude_deg: float,
    ) -> SeawaterState:
        """Convert familiar SP/in-situ temperature into the kernel state."""

        if practical_salinity < 0.0:
            raise ModelInputError("practical_salinity must be >= 0")
        pressure = self.pressure_dbar(depth_m, latitude_deg)
        absolute = float(
            self._gsw.SA_from_SP(
                float(practical_salinity),
                pressure,
                float(longitude_deg),
                float(latitude_deg),
            )
        )
        conservative = float(
            self._gsw.CT_from_t(
                absolute,
                float(in_situ_temperature_C),
                pressure,
            )
        )
        return SeawaterState(absolute, conservative)

    def density_kg_m3(
        self,
        state: SeawaterState,
        *,
        depth_m: float,
        latitude_deg: float,
    ) -> float:
        pressure = self.pressure_dbar(depth_m, latitude_deg)
        return float(
            self._gsw.rho(
                state.absolute_salinity_gkg,
                state.conservative_temperature_C,
                pressure,
            )
        )

    def in_situ_temperature_C(
        self,
        state: SeawaterState,
        *,
        depth_m: float,
        latitude_deg: float,
    ) -> float:
        pressure = self.pressure_dbar(depth_m, latitude_deg)
        return float(
            self._gsw.t_from_CT(
                state.absolute_salinity_gkg,
                state.conservative_temperature_C,
                pressure,
            )
        )
