from __future__ import annotations
import csv
import importlib.util
import yaml
import pytest
from pathlib import Path

SRC=Path(__file__).resolve().parents[2]/'tools'/'generate_time1_demo.py'
module=importlib.util.module_from_spec(importlib.util.spec_from_file_location('time1_demo_gen',SRC))
module.__spec__.loader.exec_module(module)

def test_generated_synthetic_72h_gapped_history_is_deterministic(tmp_path):
    first=module.generate_demo(tmp_path/'workspace'/'one')
    second=module.generate_demo(tmp_path/'workspace'/'two')
    assert first.read_bytes()==second.read_bytes()
    spec=yaml.safe_load(first.read_text())
    assert spec['forcing']['source']['flow_m3h']['provider']=='csv'
    assert spec['forcing']['ambient']['current_profile']['provider']=='csv_time_vector_profile'
    assert spec['workspace']['root']=='..'
    with (first.parent/'temperature.csv').open() as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==(72-1)*3
    assert len({r['time'] for r in rows})==71
    with (first.parent/'flow.csv').open() as f:
        flows=list(csv.DictReader(f))
    assert len(flows)==72
    assert len({float(r['value']) for r in flows})>2
    with (first.parent/'current.csv').open() as f:
        curr=list(csv.DictReader(f))
    assert len(curr)==72*3
    assert len({r['u_east_mps'] for r in curr})>5

def test_demo_never_overwrites_existing_data(tmp_path):
    output=tmp_path/'workspace'/'demo'
    module.generate_demo(output)
    with pytest.raises(FileExistsError):
        module.generate_demo(output)
    with pytest.raises(ValueError):
        module.generate_demo(tmp_path/'References'/'evidence')
