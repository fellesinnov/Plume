"""Headless, gap-preserving Ocean diagnostic views of normalized history inputs.

Display-only resampling *within a timestamp*; never used as model input, never
interpolates absent hours, and never substitutes for site-depth/wet-cell QA.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..errors import ProviderDataError
from ..history import HistoricalForcing


@dataclass(frozen=True)
class OceanPanel:
    clock_times: tuple[str, ...]
    depths_m: np.ndarray
    values: np.ndarray     # [depth, time], NaN for missing hours
    name: str
    units: str
    missing_columns: tuple[int, ...]
    history_sha256: str


def history_panel(history: HistoricalForcing, *, quantity: str = "temperature",
                  depth_samples: int = 61) -> OceanPanel:
    """Build an input-data matrix without loading/requerying providers."""
    history.verify_identity()
    lookup = {
        "temperature": ("ambient.temperature_profile_C", "value", "In-situ temperature", "°C"),
        "salinity": ("ambient.salinity_profile_psu", "value", "Practical salinity", "PSU"),
        "u_east": ("ambient.current_profile", "u_east_mps", "Eastward current", "m/s"),
        "v_north": ("ambient.current_profile", "v_north_mps", "Northward current", "m/s"),
    }
    if quantity not in lookup:
        raise ProviderDataError(f"unknown historical view {quantity!r}")
    if type(depth_samples) is not int or not 2 <= depth_samples <= 400:
        raise ProviderDataError("Ocean plot vertical resolution must be 2..400")
    key, variable, label, units = lookup[quantity]
    if quantity == "temperature" and history.series[key]["data_kind"] == "time_depth_potential":
        # Plot raw native Copernicus thetao honestly. Only when selecting the
        # UTC hour is it paired with SP and converted via GSW for MODEL-1.
        label = "Potential temperature θ (pt0; converts to in-situ on pin)"
    seabed = float(history.request["site"]["water_depth_m"])
    depths = np.linspace(0, seabed, depth_samples, dtype=float)
    vals = np.full((len(depths), len(history.clock_times)), np.nan, dtype=float)
    idx = history.series[key]
    for i, timestamp in enumerate(history.clock_times):
        rows = idx["records_by_time"].get(timestamp, ()) if "records_by_time" in idx else idx["records"]
        if not rows:
            continue
        if idx["data_kind"] == "vector_constant":
            vals[:, i] = float(rows[0][variable])
            continue
        xs = np.array([float(row["depth_m"]) for row in rows], dtype=float)
        ys = np.array([float(row[variable]) for row in rows], dtype=float)
        if len(xs) < 2 or xs[0] > 1e-8 or xs[-1] < seabed - 1e-8:
            # Incomplete vertical profiles are not silently extended here.
            continue
        vals[:, i] = np.interp(depths, xs, ys)
    return OceanPanel(history.clock_times, depths, vals, label, units,
                      tuple(int(i) for i in np.flatnonzero(np.all(~np.isfinite(vals), axis=0))),
                      history.data_sha256)


def render_ocean_panel(panel: OceanPanel, *, selected: str | None = None):
    """Matplotlib adapter; no model solver, cloud client, or cached data mutation."""
    from matplotlib import pyplot as plt
    from matplotlib.colors import Normalize
    import matplotlib.ticker as ticker

    n = len(panel.clock_times)
    if n == 0:
        raise ProviderDataError("cannot render an empty ocean period")
    fig, ax = plt.subplots(figsize=(12, 4.2), facecolor="#0b1520")
    ax.set_facecolor("#112535")
    field = np.ma.masked_invalid(panel.values)
    rendered = ax.imshow(field, aspect="auto", origin="upper", interpolation="nearest",
                         extent=(-.5, n-.5, panel.depths_m[-1], 0), cmap="viridis")
    fig.colorbar(rendered, ax=ax, label=f"{panel.name} [{panel.units}]")
    if selected in panel.clock_times:
        ix = panel.clock_times.index(selected)
        ax.axvline(ix, color="cyan", lw=1.4, label="Selected UTC hour")
        ax.legend(loc="upper right")
    ax.set_ylabel("Depth below surface [m]")
    ax.set_xlabel("UTC forcing timestamps (gaps remain missing)")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7, integer=True))
    from matplotlib.ticker import FuncFormatter
    ax.xaxis.set_major_formatter(FuncFormatter(lambda pos, _:panel.clock_times[max(0, min(n-1, int(round(pos))))][:10]))
    ax.set_title(f"{panel.name} history | provider data, not a thermal plume result")
    fig.tight_layout()
    return fig
