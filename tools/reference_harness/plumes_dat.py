"""Parser for PLUMES2.0 ``ModelResults_TxtOutputs.dat`` reference output.

Only the stable evidence needed by REF-1 is normalized here. Unknown prose remains raw evidence in
``References/`` and is not guessed at. The executable labels its near-field vertical coordinate
``Depth`` while printing negative values below the free surface. We therefore expose the value as
``z_m`` (surface zero, positive upward) and derive an explicit positive-down
``depth_below_surface_m``.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Iterable

_EVENT_NAMES = {
    "plume traps": "plume_traps",
    "merging happened": "merging_happened",
    "plume surfaces": "plume_surfaces",
    "plume bottoms": "plume_bottoms",
    "local maximum rise or fall": "local_maximum_rise_or_fall",
    "reached acute mixing zone": "reached_acute_mixing_zone",
    "reached chronic mixing zone": "reached_chronic_mixing_zone",
}


@dataclass(frozen=True, slots=True)
class NearFieldRow:
    step: int
    dilution_flux_avg: float
    plume_diameter_m: float
    x_m: float
    y_m: float
    z_m: float

    @property
    def depth_below_surface_m(self) -> float:
        return -self.z_m


@dataclass(frozen=True, slots=True)
class FarFieldRow:
    dilution_flux_avg: float
    width_m: float
    distance_m: float
    time_h: float


@dataclass(frozen=True, slots=True)
class Event:
    name: str
    section: str
    after_near_field_step: int | None = None
    after_far_field_distance_m: float | None = None


@dataclass(frozen=True, slots=True)
class PlumesDat:
    near_field: tuple[NearFieldRow, ...]
    events: tuple[Event, ...]
    wastefield_width_m: float | None
    far_field_diffusivity: str | None
    far_field: tuple[FarFieldRow, ...]

    def normalized(self) -> dict[str, object]:
        """Return the stable JSON-friendly REF-1 normalization shape."""
        return {
            "format": "plumes_modelresults_v1",
            "coordinates": {
                "z_m": "surface zero, positive upward",
                "depth_below_surface_m": "positive downward; derived as -z_m",
            },
            "dilution": "flux-averaged",
            "near_field": [
                {
                    "step": row.step,
                    "dilution_flux_avg": row.dilution_flux_avg,
                    "plume_diameter_m": row.plume_diameter_m,
                    "x_m": row.x_m,
                    "y_m": row.y_m,
                    "z_m": row.z_m,
                    "depth_below_surface_m": row.depth_below_surface_m,
                }
                for row in self.near_field
            ],
            "events": [
                {
                    "name": event.name,
                    "section": event.section,
                    "after_near_field_step": event.after_near_field_step,
                    "after_far_field_distance_m": event.after_far_field_distance_m,
                }
                for event in self.events
            ],
            "far_field": {
                "wastefield_width_m": self.wastefield_width_m,
                "diffusivity": self.far_field_diffusivity,
                "rows": [
                    {
                        "dilution_flux_avg": row.dilution_flux_avg,
                        "width_m": row.width_m,
                        "distance_m": row.distance_m,
                        "time_h": row.time_h,
                    }
                    for row in self.far_field
                ],
            },
        }


def _numbers(line: str) -> list[str]:
    return re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?", line)


def _event_name(line: str) -> str | None:
    lowered = line.lower()
    for marker, normalized in _EVENT_NAMES.items():
        if marker in lowered:
            return normalized
    return None


def parse_lines(lines: Iterable[str]) -> PlumesDat:
    """Parse the stable near-/far-field tables from an iterable of text lines."""
    mode = "header"
    near_field: list[NearFieldRow] = []
    far_field: list[FarFieldRow] = []
    events: list[Event] = []
    wastefield_width_m: float | None = None
    diffusivity: str | None = None

    for raw in lines:
        line = raw.rstrip("\r\n")
        stripped = line.strip()
        lowered = stripped.lower()

        if "simulation results:" in lowered:
            mode = "near_field"
            continue
        if "starting farfield calculations" in lowered:
            mode = "far_field_header"
            continue

        event = _event_name(stripped)
        if event is not None:
            if mode == "near_field":
                events.append(
                    Event(
                        event,
                        section="near_field",
                        after_near_field_step=near_field[-1].step if near_field else None,
                    )
                )
            elif mode in {"far_field_header", "far_field"}:
                events.append(
                    Event(
                        event,
                        section="far_field",
                        after_far_field_distance_m=(far_field[-1].distance_m if far_field else None),
                    )
                )
            else:
                events.append(Event(event, section="header"))
            continue

        if mode == "near_field":
            values = _numbers(stripped)
            if len(values) == 6 and re.fullmatch(r"\d+", values[0]):
                step = int(values[0])
                near_field.append(
                    NearFieldRow(
                        step=step,
                        dilution_flux_avg=float(values[1]),
                        plume_diameter_m=float(values[2]),
                        x_m=float(values[3]),
                        y_m=float(values[4]),
                        z_m=float(values[5]),
                    )
                )
            continue

        if mode in {"far_field_header", "far_field"}:
            match = re.search(
                r"Farfield dispersion based on wastefield width of\s*:\s*"
                r"([-+0-9.Ee]+)\s*\(m\)",
                stripped,
                re.IGNORECASE,
            )
            if match:
                wastefield_width_m = float(match.group(1))
                continue
            if "4/3 power law based eddy diffusivity" in lowered:
                diffusivity = "power_4_3"
                continue
            if "constant eddy diffusivity" in lowered:
                diffusivity = "constant"
                continue
            if "linear eddy diffusivity" in lowered:
                diffusivity = "linear"
                continue
            values = _numbers(stripped)
            if len(values) == 4:
                mode = "far_field"
                far_field.append(FarFieldRow(*(float(value) for value in values)))

    if not near_field:
        raise ValueError("no PLUMES near-field Simulation Results rows found")

    return PlumesDat(
        near_field=tuple(near_field),
        events=tuple(events),
        wastefield_width_m=wastefield_width_m,
        far_field_diffusivity=diffusivity,
        far_field=tuple(far_field),
    )


def parse_modelresults(path: str | Path) -> PlumesDat:
    """Parse one checked-in PLUMES ``ModelResults_TxtOutputs.dat`` file."""
    with Path(path).open("r", encoding="utf-8", errors="strict", newline=None) as handle:
        return parse_lines(handle)
