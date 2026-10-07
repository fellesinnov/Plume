"""Compare the two immutable checked-in PLUMES shipped examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .plumes_dat import PlumesDat, parse_modelresults
except ImportError:  # direct script execution from repository root
    from plumes_dat import PlumesDat, parse_modelresults  # type: ignore[no-redef]


def _near_field_signature(parsed: PlumesDat) -> list[tuple[object, ...]]:
    return [
        (
            row.step,
            row.dilution_flux_avg,
            row.plume_diameter_m,
            row.x_m,
            row.y_m,
            row.z_m,
        )
        for row in parsed.near_field
    ]


def comparison_summary(left: PlumesDat, right: PlumesDat) -> dict[str, Any]:
    """Build the deterministic summary used as REF-1 evidence."""
    left_nf = _near_field_signature(left)
    right_nf = _near_field_signature(right)
    near_identical = left_nf == right_nf
    first_nf_difference = None
    if not near_identical:
        for index, (a, b) in enumerate(zip(left_nf, right_nf, strict=False)):
            if a != b:
                first_nf_difference = {"index": index, "left": a, "right": b}
                break
        if first_nf_difference is None and len(left_nf) != len(right_nf):
            first_nf_difference = {
                "index": min(len(left_nf), len(right_nf)),
                "left": None if len(left_nf) <= len(right_nf) else left_nf[len(right_nf)],
                "right": None if len(right_nf) <= len(left_nf) else right_nf[len(left_nf)],
            }

    return {
        "format": "plumes_example_comparison_v1",
        "near_field": {
            "left_rows": len(left.near_field),
            "right_rows": len(right.near_field),
            "identical_normalized_rows": near_identical,
            "first_difference": first_nf_difference,
            "left_terminal": left.normalized()["near_field"][-1],
            "right_terminal": right.normalized()["near_field"][-1],
            "left_events": left.normalized()["events"],
            "right_events": right.normalized()["events"],
        },
        "far_field": {
            "left_diffusivity": left.far_field_diffusivity,
            "right_diffusivity": right.far_field_diffusivity,
            "same_diffusivity": left.far_field_diffusivity == right.far_field_diffusivity,
            "left_wastefield_width_m": left.wastefield_width_m,
            "right_wastefield_width_m": right.wastefield_width_m,
            "left_rows": len(left.far_field),
            "right_rows": len(right.far_field),
            "identical_normalized_rows": left.far_field == right.far_field,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    summary = comparison_summary(parse_modelresults(args.left), parse_modelresults(args.right))
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
