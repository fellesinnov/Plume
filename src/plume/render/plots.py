"""Optional Matplotlib renderer; no plotting dependency enters the FIELD core."""

from __future__ import annotations

import math

import numpy as np

from ..errors import ModelInputError
from ..field import FieldSlice


def render_field_pair(section: FieldSlice, plan: FieldSlice, *,
                      threshold_delta_T_C: float = 2.0,
                      title: str = "Plume near-field reconstruction"):
    """Return a Figure with physical section/plan and labelled temperature scales.

    The amber plume colours represent local in-situ temperature EXCESS. Pale
    blue background represents absolute ambient temperature, not excess.
    Plan is a slice at the explicitly named constant depth, never a vertical
    max-projection. No shapes are added outside reconstructed near-field data.
    """
    if section.plane != "section" or plan.plane != "plan":
        raise ModelInputError("expected (vertical section, physical horizontal plan)")
    if not math.isfinite(threshold_delta_T_C) or threshold_delta_T_C <= 0:
        raise ModelInputError("thermal threshold must be positive and finite")
    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import Normalize
        from matplotlib.cm import ScalarMappable
    except ImportError as exc:
        raise RuntimeError("rendering requires matplotlib: pip install plume-engine[plot]") from exc

    all_ambient = np.concatenate((section.values.ambient_temperature_C.ravel(),
                                  plan.values.ambient_temperature_C.ravel()))
    lo, hi = float(np.min(all_ambient)), float(np.max(all_ambient))
    if hi <= lo:
        lo, hi = lo - 0.5, hi + 0.5
    max_excess = max(0.1, float(np.max(section.values.delta_temperature_C)),
                     float(np.max(plan.values.delta_temperature_C)))
    vmax = max(threshold_delta_T_C * 1.2, max_excess)

    with plt.style.context("dark_background"):
        fig = plt.figure(figsize=(15.4, 8.7), facecolor="#111927")
        gs = fig.add_gridspec(2, 2, left=0.075, right=0.91, top=0.89,
                              bottom=0.16, width_ratios=[26, 1], hspace=0.39,
                              wspace=0.12)
        axes = (fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0]))
        delta_bar_ax = fig.add_subplot(gs[:, 1])
        for ax, field in zip(axes, (section, plan), strict=True):
            ax.set_facecolor("#102135")
            ambient = field.values.ambient_temperature_C
            dt = field.values.delta_temperature_C
            x, y = np.meshgrid(field.horizontal_axis_m, field.vertical_axis_m)
            ax.pcolormesh(x, y, ambient, cmap="Blues_r", vmin=lo, vmax=hi,
                          shading="auto", alpha=0.52)
            positive = np.ma.masked_where(~field.values.modeled | (dt <= 0.025), dt)
            plume = ax.pcolormesh(x, y, positive, cmap="inferno", vmin=0.0,
                                  vmax=vmax, shading="auto", alpha=0.95)
            if float(np.max(dt)) > threshold_delta_T_C and float(np.min(dt)) < threshold_delta_T_C:
                ax.contour(x, y, dt, levels=[threshold_delta_T_C],
                           colors=["#83f6e4"], linewidths=1.8)
            ax.grid(color="white", alpha=0.12, linewidth=0.55)
            for spine in ax.spines.values():
                spine.set_color("#5f778a")
        sec, pln = axes
        sec.invert_yaxis()
        sec.set_xlabel("Along-section distance [m]")
        sec.set_ylabel("Depth below surface [m]")
        sec.set_title(f"Vertical section | heading {section.heading_or_depth:.0f}°")
        pln.set_aspect("equal", adjustable="box")
        pln.set_xlabel("East [m]")
        pln.set_ylabel("North [m]")
        pln.set_title(f"Horizontal plan | depth {plan.heading_or_depth:.1f} m")
        pln.plot(0, 0, marker="+", color="#83f6e4", markersize=8,
                 alpha=0.7, linestyle="None", zorder=8)
        cbar = fig.colorbar(plume, cax=delta_bar_ax, orientation="vertical")
        cbar.set_label("Thermal excess ΔT [°C] vs local ambient")
        ambient_bar_ax = fig.add_axes([0.33, 0.083, 0.32, 0.016])
        cb2 = fig.colorbar(ScalarMappable(norm=Normalize(lo, hi), cmap="Blues_r"),
                           cax=ambient_bar_ax, orientation="horizontal")
        cb2.set_label("Ambient in-situ T [°C]")
        fig.suptitle(title, fontsize=17, fontweight="bold", x=0.075, y=0.96, ha="left")
        fig.text(0.075, 0.025,
                 "Reference 3/2-profile (source-bounded) • near-field ONLY • "
                 f"cyan = ΔT {threshold_delta_T_C:g}°C • unvalidated physical contours",
                 fontsize=9, alpha=0.8)
    return fig
