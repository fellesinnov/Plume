"""Interactive thermal outfall screening sensitivity tool.

Run:
    python interactive_case_sensitivity.py

This opens a simple Matplotlib slider UI with:
- flow (1000 to 20000 m3/h)
- target velocity (1 to 5 m/s)
- sea temperature (5 to 30 C)
- discharge delta-T (2 to 15 C)
- water depth (5 to 30 m)
- discharge elevation below surface (1 to 20 m)
- ambient current (0 to 1 m/s)

It then plots the centerline temperature decay for the 4 C, 3 C, and 2 C
mixing-zone criteria on one chart, and marks the approximate distance where
each criterion is reached.

A snapshot-only mode is also available for non-GUI validation:
    python interactive_case_sensitivity.py --snapshot
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

from outfall_screen import OutfallCase, CalibrationParams, simulate

DN_VALUES = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50,
             0.60, 0.65, 0.70, 0.75, 0.80, 0.90, 1.00, 1.20]


def required_diameter_for_velocity(flow_m3h: float, target_velocity_mps: float) -> float:
    q = flow_m3h / 3600.0
    area = q / target_velocity_mps
    return (4.0 * area / math.pi) ** 0.5


def nearest_standard_diameter(flow_m3h: float, target_velocity_mps: float) -> Tuple[float, float]:
    required = required_diameter_for_velocity(flow_m3h, target_velocity_mps)
    selected = min(DN_VALUES, key=lambda d: abs(d - required))
    return required, selected


def get_case_from_controls(flow_m3h: float, target_v: float, sea_temp: float,
                          delta_t: float, water_depth: float, discharge_depth_below_surface: float,
                          current: float) -> Tuple[float, float, OutfallCase]:
    required_d, selected_d = nearest_standard_diameter(flow_m3h, target_v)
    port_height = water_depth - discharge_depth_below_surface
    if port_height <= 0:
        raise ValueError(
            f"Discharge depth {discharge_depth_below_surface} m is too deep for water depth {water_depth} m."
        )

    case = OutfallCase(
        flow_m3h=flow_m3h,
        diameter_m=selected_d,
        sea_temp_C=sea_temp,
        delta_T_C=delta_t,
        water_depth_m=water_depth,
        port_height_m=port_height,
        current_mps=current,
        current_direction_deg=90.0,
        allowed_delta_T_C=1.0,
        design_dilution_factor=1.5,
        case_id="interactive_case",
    )
    return required_d, selected_d, case


def _build_case_for_criterion(base_case: OutfallCase, crit: float) -> OutfallCase:
    case = base_case.__class__(
        **{k: getattr(base_case, k) for k in base_case.__dataclass_fields__.keys()}
    )
    case.allowed_delta_T_C = crit
    case.case_id = f"dt_{crit:g}C"
    return case


def summarize_current_case(flow_m3h: float, target_v: float, sea_temp: float,
                          delta_t: float, water_depth: float, discharge_depth_below_surface: float,
                          current: float,
                          cal: CalibrationParams | None = None) -> dict:
    required_d, selected_d, base_case = get_case_from_controls(
        flow_m3h, target_v, sea_temp, delta_t, water_depth, discharge_depth_below_surface, current
    )
    cal = cal or CalibrationParams()

    criteria = []
    for crit in [4.0, 3.0, 2.0]:
        case = _build_case_for_criterion(base_case, crit)
        result = simulate(case, cal=cal)
        profile = result["profile"]
        x = profile["horizontal_distance_m"].to_numpy()
        y = profile["centerline_delta_T_C"].to_numpy()
        reached = float(x[y <= crit][0]) if (y <= crit).any() else None
        dilution_required = delta_t / crit
        dilution_green = dilution_required * 1.5
        criteria.append({
            "crit_C": crit,
            "distance_m": reached,
            "required_dilution": dilution_required,
            "green_dilution": dilution_green,
            "status": result["summary"]["status"],
            "termination": result["summary"]["termination"],
            "termination_distance_m": float(result["summary"]["termination_horizontal_distance_m"]),
            "profile": profile,
        })

    return {
        "required_diameter_m": required_d,
        "selected_diameter_m": selected_d,
        "d_avg_m": float(water_depth),
        "criteria": criteria,
        "termination": criteria[0]["termination"],
        "termination_distance_m": criteria[0]["termination_distance_m"],
        "calibration": {
            "alpha_scale": cal.alpha_scale,
            "centerline_ratio_asymptote": cal.centerline_ratio_asymptote,
            "crossflow_entrainment": cal.crossflow_entrainment,
            "drag_coefficient": cal.drag_coefficient,
        },
    }


def _draw_case_plot(flow_m3h: float, target_v: float, sea_temp: float,
                   delta_t: float, water_depth: float, discharge_depth_below_surface: float,
                   current: float, ax: plt.Axes, text_ax: plt.Axes,
                   calibration: CalibrationParams | None = None) -> None:
    summary = summarize_current_case(
        flow_m3h, target_v, sea_temp, delta_t, water_depth, discharge_depth_below_surface, current,
        cal=calibration,
    )
    required_d = summary["required_diameter_m"]
    selected_d = summary["selected_diameter_m"]
    d_avg = summary["d_avg_m"]

    ax.clear()
    if hasattr(ax, "_top_axis") and ax._top_axis is not None:
        ax._top_axis.remove()
        ax._top_axis = None

    ax.set_title(
        f"Flow {flow_m3h:.0f} m3/h | target U {target_v:.2f} m/s | pipe D {selected_d:.3f} m "
        f"(required {required_d:.3f} m)",
        pad=10,
    )
    ax.set_xlabel("Horizontal distance from outlet (m)")
    ax.set_ylabel("Centerline temperature difference to ambient (C)")
    ax.grid(True, alpha=0.25)
    ax.set_ylim(0, max(delta_t * 1.6, 10.0))

    max_x = 0.0
    offset_map = {
        4.0: (12, 10),
        3.0: (12, -10),
        2.0: (12, 10),
    }
    for item in summary["criteria"]:
        profile = item["profile"]
        x = profile["horizontal_distance_m"].to_numpy()
        y = profile["centerline_delta_T_C"].to_numpy()
        if len(x):
            max_x = max(max_x, float(x[-1]))
        ax.plot(x, y, label=f"dT <= {item['crit_C']:.0f} C", linewidth=2)

        hit_mask = y <= item["crit_C"]
        if hit_mask.any():
            x_hit = float(x[hit_mask][0])
            y_hit = float(y[hit_mask][0])
            ax.scatter([x_hit], [y_hit], s=50, zorder=5)
            dx, dy = offset_map.get(item["crit_C"], (8, 8))
            ax.annotate(
                f"{x_hit:.1f} m",
                (x_hit, y_hit),
                xytext=(dx, dy),
                textcoords="offset points",
                fontsize=8,
                ha="left",
                va="bottom",
                bbox={"boxstyle": "round,pad=0.15", "facecolor": "white", "alpha": 0.8, "edgecolor": "0.7"},
            )
        ax.axhline(item["crit_C"], linestyle="--", color="gray", linewidth=0.8, alpha=0.5)

    xmax = max(200.0, max_x + max(50.0, 0.35 * max_x))
    ax.set_xlim(0, xmax)
    ax.legend(fontsize=9, loc="upper right")

    ax2 = ax.twiny()
    ax._top_axis = ax2
    ax2.set_xlim(ax.get_xlim())
    n_ticks = max(1, int(math.ceil(xmax / max(d_avg, 1e-6))))
    ticks = [d_avg * i for i in range(n_ticks + 1)]
    ticks = [t for t in ticks if 0 <= t <= xmax]
    if len(ticks) > 10:
        tick_index = list(range(0, len(ticks), max(1, len(ticks) // 10)))
        ticks = [ticks[i] for i in tick_index]
    labels = [f"{idx}x" for idx in range(len(ticks))]
    ax2.set_xticks(ticks)
    ax2.set_xticklabels(labels, fontsize=9)
    ax2.set_xlabel("Distance / D_avg")

    text_ax.clear()
    text_ax.axis("off")
    lines = [
        f"D_avg = {d_avg:.1f} m",
        f"Pipe D = {selected_d:.3f} m",
        f"Req. D = {required_d:.3f} m",
        "",
        f"Termination: {summary['termination']}",
        f"End x: {summary['termination_distance_m']:.1f} m",
        "",
        "Model params:",
        f"alpha_scale = {summary['calibration']['alpha_scale']:.2f}",
        f"centerline_ratio = {summary['calibration']['centerline_ratio_asymptote']:.2f}",
        f"crossflow_entr = {summary['calibration']['crossflow_entrainment']:.2f}",
        f"drag_coeff = {summary['calibration']['drag_coefficient']:.2f}",
        "",
    ]
    for item in summary["criteria"]:
        dist = item["distance_m"]
        dist_text = "not reached" if dist is None else f"{dist:.1f} m"
        lines.append(f"dT <= {item['crit_C']:.0f} C: {dist_text}")
        lines.append(f"  required dilution = {item['required_dilution']:.2f}:1")
        lines.append(f"  green target      = {item['green_dilution']:.2f}:1")
        if item["termination"]:
            lines.append(f"  stop: {item['termination']}")
        lines.append("")

    text_ax.text(
        0.02,
        0.98,
        "\n".join(lines),
        va="top",
        ha="left",
        fontsize=9,
        family="monospace",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )


def _build_figure_layout(figsize=(15, 9)):
    fig = plt.figure(figsize=figsize)
    plot_ax = fig.add_axes([0.08, 0.30, 0.61, 0.58])
    summary_ax = fig.add_axes([0.73, 0.39, 0.23, 0.42])
    return fig, plot_ax, summary_ax


def _add_slider_group(fig, specs, left, right, y0, height=0.025, gap=0.035):
    sliders = {}
    section_y = y0
    for label, low, high, init, step, *extra in specs:
        ax_slider = fig.add_axes([left, section_y, right - left, height])
        slider_label = label
        if extra and extra[0]:
            slider_label = f"{label} ({extra[0]})"
        slider = Slider(ax_slider, slider_label, low, high, valinit=init, valstep=step)
        sliders[label] = slider
        section_y -= gap
    return sliders


def run_interactive() -> None:
    fig, ax, txt_ax = _build_figure_layout(figsize=(15, 9))

    def update(_val):
        flow = flow_slider.val
        target_v = vel_slider.val
        sea_temp = sea_slider.val
        delta_t = dt_slider.val
        water_depth = depth_slider.val
        discharge_depth = discharge_slider.val
        current = current_slider.val
        cal = CalibrationParams(
            alpha_scale=alpha_scale_slider.val,
            centerline_ratio_asymptote=centerline_ratio_slider.val,
            crossflow_entrainment=crossflow_slider.val,
            drag_coefficient=drag_slider.val,
        )
        _draw_case_plot(flow, target_v, sea_temp, delta_t, water_depth, discharge_depth, current, ax, txt_ax, calibration=cal)
        fig.canvas.draw_idle()

    input_specs = [
        ("Flow", 1000.0, 20000.0, 3000.0, 100.0),
        ("Target velocity", 1.0, 5.0, 2.0, 0.1),
        ("Sea temp", 5.0, 30.0, 20.0, 0.5),
        ("dT discharge", 2.0, 15.0, 7.0, 0.5),
        ("Water depth", 5.0, 30.0, 10.0, 0.5),
        ("Discharge depth", 1.0, 20.0, 7.0, 0.5),
        ("Current", 0.0, 1.0, 0.0, 0.05),
    ]
    calibration_specs = [
        ("alpha_scale", 0.10, 1.50, 0.35, 0.05, "Overall dilution rate"),
        ("centerline_ratio", 1.00, 3.00, 2.00, 0.05, "Bulk-to-centerline conversion"),
        ("crossflow_entrainment", 0.10, 1.00, 0.50, 0.05, "Crossflow entrainment"),
        ("drag_coeff", 0.50, 2.50, 1.30, 0.05, "Trajectory bending / crossflow drag"),
    ]

    fig.text(0.08, 0.23, "Case inputs", fontsize=10, fontweight="bold")
    fig.text(0.48, 0.23, "Model parameters", fontsize=10, fontweight="bold")

    input_sliders = _add_slider_group(fig, input_specs, 0.08, 0.42, 0.20, height=0.022, gap=0.032)
    calibration_sliders = _add_slider_group(fig, calibration_specs, 0.48, 0.92, 0.20, height=0.022, gap=0.032)

    flow_slider = input_sliders["Flow"]
    vel_slider = input_sliders["Target velocity"]
    sea_slider = input_sliders["Sea temp"]
    dt_slider = input_sliders["dT discharge"]
    depth_slider = input_sliders["Water depth"]
    discharge_slider = input_sliders["Discharge depth"]
    current_slider = input_sliders["Current"]
    alpha_scale_slider = calibration_sliders["alpha_scale"]
    centerline_ratio_slider = calibration_sliders["centerline_ratio"]
    crossflow_slider = calibration_sliders["crossflow_entrainment"]
    drag_slider = calibration_sliders["drag_coeff"]

    for slider in [*input_sliders.values(), *calibration_sliders.values()]:
        slider.on_changed(update)

    update(None)
    plt.show()


def generate_snapshot(output_path: str | Path = "example_outputs/interactive_case_snapshot.png") -> None:
    flow = 3000.0
    target_v = 2.0
    sea_temp = 20.0
    delta_t = 7.0
    water_depth = 10.0
    discharge_depth = 7.0
    current = 0.0

    fig, ax, txt_ax = _build_figure_layout(figsize=(15, 9))
    _draw_case_plot(flow, target_v, sea_temp, delta_t, water_depth, discharge_depth, current, ax, txt_ax)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved snapshot to {Path(output_path).resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive thermal outfall sensitivity tool")
    parser.add_argument("--snapshot", action="store_true", help="Generate a static PNG instead of opening the slider UI")
    args = parser.parse_args()

    if args.snapshot:
        generate_snapshot()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
