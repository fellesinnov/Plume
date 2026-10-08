"""FIELD-1 deterministic/discriminator tests on an injected, non-physical trajectory."""

import math
from dataclasses import dataclass

import numpy as np
import pytest

from plume.errors import ModelInputError
from plume.field import (
    PEAK_TO_MEAN_LIMIT, PROFILE_ID, horizontal_plan, radial_weight,
    reconstruct_points, vertical_section,
)


@dataclass(frozen=True)
class State:
    absolute_salinity_gkg: float
    conservative_temperature_C: float


@dataclass(frozen=True)
class Level:
    depth_m: float
    seawater: State


class Column:
    levels = (Level(0., State(35., 11.)), Level(10., State(35., 9.)),
              Level(20., State(35., 7.)))


class SimpleThermo:
    def in_situ_temperature_C(self, state, *, depth_m, latitude_deg):
        return state.conservative_temperature_C + 0.01 * (state.absolute_salinity_gkg - 35.)


@dataclass
class FakeTrajectory:
    time_s: np.ndarray
    x_east_m: np.ndarray
    y_north_m: np.ndarray
    z_up_m: np.ndarray
    depth_m: np.ndarray
    diameter_m: np.ndarray
    dilution: np.ndarray
    conservative_temperature_C: np.ndarray
    absolute_salinity_gkg: np.ndarray

    def __len__(self):
        return len(self.time_s)


def straight(*, radius=1.0, dilution=5.0, anomaly=3.0, salinity=35., north=0., depth=10.):
    n = 4
    x = np.linspace(0, 9, n)
    return FakeTrajectory(
        time_s=np.arange(n, dtype=float), x_east_m=x,
        y_north_m=np.full(n, north), z_up_m=np.full(n, -depth),
        depth_m=np.full(n, depth), diameter_m=np.full(n, radius * 2.),
        dilution=np.full(n, dilution),
        conservative_temperature_C=np.full(n, 9. + anomaly),
        absolute_salinity_gkg=np.full(n, salinity),
    )


def field(t, x, y=0., z=10., chunk_size=2):
    return reconstruct_points(
        t, ambient=Column(), thermodynamics=SimpleThermo(),
        latitude_deg=60., water_depth_m=20., east_m=x, north_m=y,
        depth_m=z, chunk_size=chunk_size)


def test_integrated_profile_mass_mean_is_exact_in_developed_and_near_source_limits():
    r = np.linspace(0, 1, 20001)
    for dilution, peak in ((1., 1.), (2., 2.), (4., PEAK_TO_MEAN_LIMIT), (10., PEAK_TO_MEAN_LIMIT)):
        w = radial_weight(r, dilution)
        avg = np.sum(np.diff(r) * (r[1:] * w[1:] + r[:-1] * w[:-1]))
        assert abs(avg - 1.) < 1e-7
        assert radial_weight(0., dilution) == pytest.approx(peak)
        assert radial_weight(1.01, dilution) == 0.
    assert PROFILE_ID.startswith("plumes20_three_half")


def test_straight_profile_matches_analytic_centre_and_radius_and_thermal_salinity():
    data = field(straight(), x=np.array([3., 3., 3., 3.]),
                 y=np.array([0., 0.5, 1., 1.01]))
    expect = 3. * radial_weight(np.array([0., .5, 1., 1.01]), 5.)
    np.testing.assert_allclose(data.delta_temperature_C, expect, atol=1e-12)
    assert data.modeled.tolist() == [True, True, True, False]
    assert data.qualification.endswith("open")


def test_no_axial_endpoint_extrapolation_or_outside_support():
    data = field(straight(), x=np.array([-.2, 0., 9., 9.2, 3.]),
                 y=np.array([0., 0., 0., 0., 1.1]))
    assert data.modeled.tolist() == [False, True, True, False, False]
    assert data.delta_temperature_C[0] == data.delta_temperature_C[3] == 0.


def test_off_plane_centerline_does_not_fabricate_section_hotspot():
    data = field(straight(north=3.), x=np.array([3., 3.]), y=np.array([0., 3.]))
    assert data.delta_temperature_C[0] == 0.
    assert data.delta_temperature_C[1] > 0.


def test_diameter_and_dilution_alter_threshold_extent():
    small = field(straight(radius=.5), x=4., y=.75)
    large = field(straight(radius=1.), x=4., y=.75)
    assert not bool(small.modeled)
    assert bool(large.modeled)
    assert float(large.delta_temperature_C) > 0.
    young = field(straight(dilution=1.), x=4., y=0.)
    developed = field(straight(dilution=6.), x=4., y=0.)
    assert float(young.delta_temperature_C) == pytest.approx(3.)
    assert float(developed.delta_temperature_C) == pytest.approx(3. * PEAK_TO_MEAN_LIMIT)


def test_local_ambient_is_at_local_depth_not_centerline_depth():
    data = field(straight(radius=2.), x=np.array([4., 4.]), z=np.array([10., 11.]))
    np.testing.assert_allclose(data.ambient_temperature_C, np.array([9., 8.8]))
    assert data.delta_temperature_C[0] > data.delta_temperature_C[1] > 0.


def test_salinity_transport_reaches_zero_without_negative_at_source():
    t = straight(dilution=1., salinity=0.)
    data = field(t, x=3., y=0.)
    assert float(data.delta_absolute_salinity_gkg) == pytest.approx(-35.)
    assert math.isfinite(float(data.delta_temperature_C))


def test_invalid_physical_depth_and_trajectory_mutation_fail():
    with pytest.raises(ModelInputError):
        field(straight(), x=3., z=-0.1)
    t = straight()
    t.depth_m[1] = 2.  # deliberate coordinate-sign discriminator
    with pytest.raises(ModelInputError):
        field(t, x=3.)


def test_chunk_boundaries_do_not_change_solution():
    t = straight()
    x, y = np.meshgrid(np.linspace(-1, 10, 31), np.linspace(-1.4, 1.4, 17))
    a = field(t, x, y, chunk_size=3)
    b = field(t, x, y, chunk_size=100000)
    np.testing.assert_array_equal(a.modeled, b.modeled)
    np.testing.assert_allclose(a.delta_temperature_C, b.delta_temperature_C)


def test_curved_path_nearest_true_3d_segment():
    t = straight()
    t.y_north_m[:] = [0., 0., 2., 2.]
    assert float(field(t, x=7., y=2.).delta_temperature_C) > 0.
    assert float(field(t, x=7., y=-2.).delta_temperature_C) == 0.


def test_renderer_is_lazy_and_does_not_change_model_data():
    pytest.importorskip("matplotlib")  # optional plotting extra
    from plume.field import FieldSlice
    from plume.render import render_field_pair
    x = np.linspace(-1., 10., 61)
    z = np.linspace(0., 20., 71)
    u, d = np.meshgrid(x, z)
    t = straight()
    v1 = field(t, x=u, z=d)
    sec = FieldSlice(v1, "section", x, z, 90.)
    east = np.linspace(-1., 10., 61)
    north = np.linspace(-2., 2., 51)
    xx, yy = np.meshgrid(east, north)
    v2 = field(t, x=xx, y=yy)
    plan = FieldSlice(v2, "plan", east, north, 10.)
    original = v1.delta_temperature_C.copy()
    import matplotlib
    matplotlib.use("Agg")
    fig = render_field_pair(sec, plan, threshold_delta_T_C=2.)
    assert len(fig.axes) >= 4  # 2 views + 2 labelled colourbars
    np.testing.assert_array_equal(v1.delta_temperature_C, original)
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_invalid_radial_inputs_fail():
    with pytest.raises(ModelInputError):
        radial_weight(-0.1, 3.)
    with pytest.raises(ModelInputError):
        radial_weight(0.1, 0.2)
    with pytest.raises(ModelInputError):
        radial_weight(np.nan, 2.)


def test_solution_wrappers_pin_section_heading_and_plan_depth_without_provider_access():
    @dataclass
    class Port:
        azimuth_deg: float = 90.

    class Problem:
        ambient = Column()
        latitude_deg = 60.
        water_depth_m = 20.
        port = Port()

    class Solution:
        problem = Problem()
        thermodynamics = SimpleThermo()
        end_time_s = 3.

        def sample(self, times):
            assert times[0] == 0. and times[-1] == 3.
            return straight()

    solution = Solution()
    section = vertical_section(solution, distances_m=[0., 3., 6., 9.],
                               depths_m=[8., 10., 12.], samples=4)
    assert section.plane == "section"
    assert section.heading_or_depth == pytest.approx(90.)
    assert section.values.delta_temperature_C.shape == (3, 4)
    plan = horizontal_plan(solution, east_m=[0., 3., 6., 9.],
                           north_m=[-1., 0., 1.], depth_m=10., samples=4)
    assert plan.plane == "plan" and plan.heading_or_depth == 10.
    assert plan.values.delta_temperature_C.shape == (3, 4)
    assert plan.values.modeled[1, 1]


def test_real_gsw_conversion_smoke_if_installed():
    pytest.importorskip("gsw")
    from plume.model.thermodynamics import GswThermodynamics, SeawaterState
    thermo = GswThermodynamics()
    state = thermo.from_practical_salinity_in_situ(
        practical_salinity=35., in_situ_temperature_C=10.,
        depth_m=10., latitude_deg=60., longitude_deg=5.)
    assert math.isfinite(thermo.in_situ_temperature_C(state, depth_m=10., latitude_deg=60.))


def test_incomplete_ambient_profile_rejected_not_silently_extrapolated():
    class TruncatedColumn:
        levels = (Level(2., State(35., 11.)), Level(15., State(35., 9.)))

    with pytest.raises(ModelInputError, match="full water column"):
        reconstruct_points(straight(), ambient=TruncatedColumn(),
                           thermodynamics=SimpleThermo(), latitude_deg=60.,
                           water_depth_m=20., east_m=3., north_m=0., depth_m=10.)


def test_cold_plume_values_remain_physical_but_warm_only_plot_rejects_them():
    values = field(straight(anomaly=-3.), x=4.)
    assert float(values.delta_temperature_C) < 0.
    from plume.field import FieldSlice
    from plume.render import render_field_pair
    cold = FieldSlice(values, "section", np.array([0., 1.]), np.array([0., 1.]), 90.)
    warm = FieldSlice(values, "plan", np.array([0., 1.]), np.array([0., 1.]), 10.)
    with pytest.raises(ModelInputError, match="warm-only"):
        render_field_pair(cold, warm)
