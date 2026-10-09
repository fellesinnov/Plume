"""Generate deterministic synthetic TIME-1 Ocean/Simulate demo under ignored workspace.

NO Copernicus download, NO measured data, NO physical validation. Does not
modify `References/` or tracked source. Safe to rerun in a new output folder.
"""
from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml


def generate_demo(destination: Path, *, hours: int = 72) -> Path:
    destination = Path(destination).expanduser().resolve()
    if not 3 <= hours <= 336:
        raise ValueError("choose 3..336 demo hours")
    # Refuse writing anywhere inside immutable third-party evidence.
    if "References" in destination.parts:
        raise ValueError("never generate demo files inside References/")
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise FileExistsError("demo output directory must be empty; never overwrite existing customer data")
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    gaps = {start+timedelta(hours=37)}
    raw = {name: [] for name in ("temperature.csv", "salinity.csv", "current.csv", "flow.csv", "delta.csv")}
    for i in range(hours):
        at = start+timedelta(hours=i)
        stamp = at.isoformat(timespec="seconds").replace("+00:00", "Z")
        cycle = math.sin(2*math.pi*i/24)
        tide = math.sin(2*math.pi*i/12.42)
        raw["flow.csv"].append((stamp, round(540+85*cycle, 5)))
        raw["delta.csv"].append((stamp, round(10+1.2*math.sin(2*math.pi*i/48), 5)))
        for d in (0., 12., 25.):
            # one intentionally missing UTC hour across the entire T profile
            if at not in gaps:
                raw["temperature.csv"].append((stamp, d, round(13.-.16*d+1.1*cycle*math.exp(-d/18), 5)))
            raw["salinity.csv"].append((stamp, d, round(34.5+.020*d+.05*cycle, 5)))
            raw["current.csv"].append((stamp, d, round((.10+.07*tide)*math.exp(-d/50), 6),
                                        round((.02+.05*math.cos(2*math.pi*i/12.42))*math.exp(-d/50), 6)))
    names = {"temperature.csv":("time","depth_m","value"),
             "salinity.csv":("time","depth_m","value"),
             "current.csv":("time","depth_m","u_east_mps","v_north_mps"),
             "flow.csv":("time","value"), "delta.csv":("time","value")}
    for name,header in names.items():
        path = destination/name
        if path.exists():
            raise FileExistsError(f"demo input exists; use a new destination instead of overwriting {path}")
        with path.open("w",newline="",encoding="utf-8") as f:
            writer = csv.writer(f,lineterminator="\n")
            writer.writerow(header)
            writer.writerows(raw[name])
    end = start + timedelta(hours=hours)
    data = {
        "schema_version":1,
        "project":{"id":"time1_demo","name":"TIME-1 synthetic history (UNVALIDATED)"},
        "site":{"latitude_deg":60.0,"longitude_deg":5.0,"water_depth_m":25.0},
        "outfall":{"type":"single_round_port","diameter_m":.35,
                   "discharge_depth_below_surface_m":12.,"vertical_angle_deg":15.,"azimuth_deg":90.},
        "forcing":{
            "clock":{"start":start.isoformat(timespec="seconds").replace("+00:00","Z"),
                     "end":end.isoformat(timespec="seconds").replace("+00:00","Z"),"step":"PT1H"},
            "source":{"flow_m3h":{"provider":"csv","path":"flow.csv","time_column":"time","value_column":"value"},
                      "delta_T_C":{"provider":"csv","path":"delta.csv","time_column":"time","value_column":"value"}},
            "ambient":{
                "temperature_profile_C":{"provider":"csv_time_depth_profile","path":"temperature.csv"},
                "salinity_profile_psu":{"provider":"csv_time_depth_profile","path":"salinity.csv"},
                "current_profile":{"provider":"csv_time_vector_profile","path":"current.csv"}}},
        "model":{"near_field":{"enabled":True,"options":{"max_time_s":8.,"oscillation_event_limit":20}},
                 "field_reconstruction":{"enabled":True},"far_field":{"enabled":False}},
        "criteria":[{"id":"dt2","type":"isotherm_extent","threshold_delta_T_C":2.}],
        "workspace":{"root":"..","shared_provider_cache":True},
        "outputs":{"save":{"forcing_snapshot":True,"timestep_metrics":True,
                           "spatial_fields":"selected","section_plots":True,"plan_plots":True}},
    }
    path=destination/'history_demo.yaml'
    if path.exists():
        raise FileExistsError(f"demo config exists, will not overwrite: {path}")
    path.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8')
    return path


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('workspace/time1_demo'),
                        help='ignored workspace directory (must be new/empty)')
    parser.add_argument('--hours',type=int,default=72)
    args=parser.parse_args()
    print('Synthetic config:',generate_demo(args.output,hours=args.hours))


if __name__=='__main__':
    main()
