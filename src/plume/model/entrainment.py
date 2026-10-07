"""Single-port entrainment closures used by MODEL-1 qualification.

The Lagrangian-control-volume structure and UM3-reference closure in this
module are adapted from Ebb Carbon's MIT-licensed ``Plumes_Public`` repository,
pinned by Plume REF-1 at commit 9791c80ff94f706603df0ae473667ccdffd359db.
The GPL SFEI Visual Plumes implementation is an independent oracle only and is
not copied here.

Two closures intentionally remain behind one interface while MODEL-CLOSURE-1
is open:

* ``Um3ReferenceEntrainment`` reproduces the decoded software-reference
  Taylor/cylinder coupling for single plumes, including the observed inert
  curvature term.
* ``PublishedPaeEntrainment`` keeps the published projected-area decomposition
  as the physical qualification candidate.

Neither is exposed as a customer-facing theory selector.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray


_VERTICAL = np.array([0.0, 0.0, 1.0], dtype=np.float64)


class ClosureKind(StrEnum):
    UM3_REFERENCE = "um3_reference"
    PUBLISHED_PAE = "published_pae"


@dataclass(frozen=True, slots=True)
class LocalFrame:
    along: NDArray[np.float64]
    in_plane: NDArray[np.float64]
    out_of_plane: NDArray[np.float64]

    def components(self, vector: NDArray[np.float64]) -> tuple[float, float, float]:
        return (
            float(np.dot(vector, self.along)),
            float(np.dot(vector, self.in_plane)),
            float(np.dot(vector, self.out_of_plane)),
        )


def _cross3(a: NDArray[np.float64], b: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.array(
        [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        ],
        dtype=np.float64,
    )


def vertical_plane_frame(
    plume_velocity: NDArray[np.float64],
    ambient_velocity: NDArray[np.float64] | None = None,
) -> LocalFrame:
    """Frame whose working plane is vertical and contains the trajectory.

    A perfectly vertical trajectory is degenerate; in that case the plane is
    chosen to contain the ambient current so a horizontal cross-current does
    not disappear into an arbitrary axis convention.
    """

    speed = float(np.linalg.norm(plume_velocity))
    if speed <= 0.0:
        raise ValueError("the local frame is undefined for a motionless element")
    along = plume_velocity / speed
    normal = _cross3(along, _VERTICAL)
    if float(np.linalg.norm(normal)) < 1e-12 and ambient_velocity is not None:
        normal = _cross3(along, ambient_velocity)
    if float(np.linalg.norm(normal)) < 1e-12:
        normal = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    out_of_plane = normal / float(np.linalg.norm(normal))
    in_plane = _cross3(out_of_plane, along)
    return LocalFrame(along=along, in_plane=in_plane, out_of_plane=out_of_plane)


def taylor_area(radius_m: float, thickness_m: float) -> float:
    return 2.0 * math.pi * radius_m * thickness_m


@dataclass(frozen=True, slots=True)
class ProjectedArea:
    growth_m2: float
    cylinder_m2: float
    curvature_m2: float

    @property
    def in_plane_total_m2(self) -> float:
        return max(0.0, self.cylinder_m2 + self.curvature_m2)


def projected_area(
    radius_m: float,
    thickness_m: float,
    radius_gradient: float,
    elevation_gradient: float,
) -> ProjectedArea:
    """Published PAE areas for db/ds and d(theta)/ds."""

    return ProjectedArea(
        growth_m2=math.pi * radius_m * radius_gradient * thickness_m,
        cylinder_m2=2.0 * radius_m * thickness_m,
        curvature_m2=(
            -0.5
            * math.pi
            * radius_m
            * radius_m
            * elevation_gradient
            * thickness_m
        ),
    )


class EntrainmentClosure:
    kind: ClosureKind

    def rate_kg_s(
        self,
        *,
        ambient_density_kg_m3: float,
        ambient_velocity_mps: NDArray[np.float64],
        plume_velocity_mps: NDArray[np.float64],
        radius_m: float,
        thickness_m: float,
        radius_gradient: float,
        elevation_gradient: float,
        aspiration_coefficient: float,
    ) -> float:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Um3ReferenceEntrainment(EntrainmentClosure):
    """Decoded single-plume UM3 software-reference entrainment closure."""

    growth_weight: float = 1.0
    curvature_weight: float = 0.0
    out_of_plane_weight: float = 1.0
    kind: ClosureKind = ClosureKind.UM3_REFERENCE

    def rate_kg_s(
        self,
        *,
        ambient_density_kg_m3: float,
        ambient_velocity_mps: NDArray[np.float64],
        plume_velocity_mps: NDArray[np.float64],
        radius_m: float,
        thickness_m: float,
        radius_gradient: float,
        elevation_gradient: float,
        aspiration_coefficient: float,
    ) -> float:
        if aspiration_coefficient < 0.0:
            raise ValueError("aspiration_coefficient must be non-negative")
        speed = float(np.linalg.norm(plume_velocity_mps))
        if speed <= 0.0:
            raise ValueError("entrainment is undefined for a motionless element")
        frame = vertical_plane_frame(plume_velocity_mps, ambient_velocity_mps)
        out_of_plane_current = float(np.dot(ambient_velocity_mps, frame.out_of_plane))
        in_plane_current = ambient_velocity_mps - out_of_plane_current * frame.out_of_plane
        along = float(np.dot(in_plane_current, frame.along))
        across = float(np.linalg.norm(in_plane_current)) * abs(plume_velocity_mps[2]) / speed

        shear = aspiration_coefficient * abs(speed - along)
        angle = math.atan(math.sqrt(across / shear - 1.0)) if across > shear > 0.0 else 0.0
        reduced = shear * (1.0 - angle / math.pi) - (
            across / math.pi
        ) * (1.0 - math.sin(angle))
        areas = projected_area(
            radius_m,
            thickness_m,
            radius_gradient,
            elevation_gradient,
        )
        paired = ambient_density_kg_m3 * (
            taylor_area(radius_m, thickness_m) * reduced
            + areas.cylinder_m2 * across
        )
        same_growth_direction = (along > 0.0) == (radius_gradient > 0.0)
        growth = (
            self.growth_weight
            * ambient_density_kg_m3
            * abs(along)
            * max(0.0, areas.growth_m2)
            if same_growth_direction
            else 0.0
        )
        curvature = (
            self.curvature_weight
            * ambient_density_kg_m3
            * across
            * areas.curvature_m2
        )
        sideways = (
            self.out_of_plane_weight
            * ambient_density_kg_m3
            * abs(out_of_plane_current)
            * areas.cylinder_m2
        )
        return max(0.0, paired + growth + curvature + sideways)


@dataclass(frozen=True, slots=True)
class PublishedPaeEntrainment(EntrainmentClosure):
    """Published projected-area candidate with ambient-relative Taylor shear."""

    kind: ClosureKind = ClosureKind.PUBLISHED_PAE

    def rate_kg_s(
        self,
        *,
        ambient_density_kg_m3: float,
        ambient_velocity_mps: NDArray[np.float64],
        plume_velocity_mps: NDArray[np.float64],
        radius_m: float,
        thickness_m: float,
        radius_gradient: float,
        elevation_gradient: float,
        aspiration_coefficient: float,
    ) -> float:
        if aspiration_coefficient < 0.0:
            raise ValueError("aspiration_coefficient must be non-negative")
        relative_speed = float(
            np.linalg.norm(plume_velocity_mps - ambient_velocity_mps)
        )
        taylor = (
            ambient_density_kg_m3
            * taylor_area(radius_m, thickness_m)
            * aspiration_coefficient
            * relative_speed
        )
        frame = vertical_plane_frame(plume_velocity_mps, ambient_velocity_mps)
        along, in_plane, _ = frame.components(ambient_velocity_mps)
        areas = projected_area(
            radius_m,
            thickness_m,
            radius_gradient,
            elevation_gradient,
        )
        forced = ambient_density_kg_m3 * (
            abs(along) * max(0.0, areas.growth_m2)
            + abs(in_plane) * areas.in_plane_total_m2
        )
        return max(0.0, taylor + forced)


def closure_from_kind(kind: ClosureKind) -> EntrainmentClosure:
    if kind is ClosureKind.UM3_REFERENCE:
        return Um3ReferenceEntrainment()
    if kind is ClosureKind.PUBLISHED_PAE:
        return PublishedPaeEntrainment()
    raise ValueError(f"unsupported closure kind: {kind}")
