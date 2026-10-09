"""Bounded runner tests against its REAL authored headless module and contract stubs."""
from __future__ import annotations
import copy, json
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import pytest
from plume.config import LoadedConfig
from plume.design.snapshot import _digest
from plume.design.projects import DesignProject
from plume.errors import ProviderDataError,WorkspaceError
from plume.runner.history_run import restored_forcing_config,preflight_history,run_history,load_historical_run

TIMES=[f'2025-01-0{i}T00:00:00Z' for i in (1,2,3)]
SITE={'latitude_deg':60.,'longitude_deg':5.,'water_depth_m':20.}
ORIGINAL={'flow_m3h':{'provider':'csv','path':'flow.csv','time_column':'time','value_column':'value'},
          'delta_T_C':{'provider':'csv','path':'delta.csv','time_column':'time','value_column':'value'}}
AMBIENT={'temperature_profile_C':{'provider':'inline_profile','levels':[{'depth_m':0,'value':10},{'depth_m':20,'value':7}]},
         'salinity_profile_psu':{'provider':'inline_profile','levels':[{'depth_m':0,'value':34},{'depth_m':20,'value':35}]},
         'current_profile':{'provider':'constant_vector','u_east_mps':.1,'v_north_mps':0.}}

def fixture(tmp_path):
    raw={'schema_version':1,'project':{'id':'demo','name':'Demo'},'site':SITE,
         'outfall':{'type':'single_round_port','diameter_m':1.0,'discharge_depth_below_surface_m':12.,'vertical_angle_deg':0.,'azimuth_deg':90.},
         'forcing':{'clock':{'start':TIMES[0],'end':'2025-01-04T00:00:00Z','step':'P1D'},
                    'source':{'flow_m3h':{'provider':'constant','value':500.},'delta_T_C':{'provider':'constant','value':10.}},'ambient':AMBIENT},
         'model':{'near_field':{'enabled':True},'far_field':{'enabled':False}},
         'criteria':[{'id':'dt2','type':'isotherm_extent','threshold_delta_T_C':2.}],
         'workspace':{'root':'workspace','shared_provider_cache':True},'outputs':{'save':{'spatial_fields':'selected'}}}
    cfg=LoadedConfig(tmp_path/'projects'/'demo'/'project.yaml',raw,_digest(raw))
    root=tmp_path/'projects'/'demo';(root/'runs').mkdir(parents=True)
    project=DesignProject(root,cfg,'20261009T120000Z-d9f0ed42',cfg.sha256)
    pinned=SimpleNamespace(source_specs=ORIGINAL,site=SITE,ambient_spec_sha256=_digest(AMBIENT),
                           verify_identity=lambda:None)
    class FakeStore:
        def __init__(self,project,snapshot):self.project=project;self.snapshot=snapshot
        def open(self,project_id):return self.project
        def load_locked_snapshot(self,project):return self.snapshot
    store=FakeStore(project,pinned)
    class History:
        def __init__(self):
            self.available_times=(TIMES[0],TIMES[2])
            self.clock_times=tuple(TIMES)
            self.missing_by_time={TIMES[1]:('source.flow_m3h',)}
            self.data_sha256='a'*64
            self.request_sha256='b'*64
            self.request={'source':ORIGINAL,'ambient':AMBIENT,'site':SITE,'clock':raw['forcing']['clock']}
            self.calls=[]
        def verify_identity(self):pass
        def _require_config(self,cfg):
            assert cfg.normalized['forcing']['source']==ORIGINAL
            assert cfg.normalized['site']==SITE
        def snapshot_at(self,cfg,t):
            self.calls.append(('snapshot_at',t));self._require_config(cfg)
            return SimpleNamespace(snapshot_sha256='c'*64,source_scalars={'flow_m3h':600. if t==TIMES[0] else 1200.,'delta_T_C':10.})
        def _snapshot_unchecked(self,t):
            self.calls.append(('unchecked',t))
            return SimpleNamespace(snapshot_sha256='c'*64,source_scalars={'flow_m3h':600. if t==TIMES[0] else 1200.,'delta_T_C':10.})
    return project,store,History()


def evaluator(c,p,*,section_resolution,plan_resolution):
    assert c['forcing']['source']==ORIGINAL
    assert section_resolution==(41,31)
    flow=p.source_scalars['flow_m3h']
    return SimpleNamespace(metrics={
        'section_peak_delta_T_C':flow/100.,'plan_peak_delta_T_C':flow/200.,
        'final_bulk_dilution':3+flow/400.,'plan_threshold_farthest_radius_m':flow/30.,
        'threshold_delta_T_C':2.,'termination_reason':'duration'})


def test_original_plant_provider_restored_before_preflight(tmp_path):
    project,store,h=fixture(tmp_path)
    source=restored_forcing_config(project,store)
    assert source.normalized['forcing']['source']==ORIGINAL
    assert project.config.normalized['forcing']['source']['flow_m3h']['provider']=='constant'
    assert source.normalized['outfall']==project.config.normalized['outfall']
    pf=preflight_history(project,store,h)
    assert pf.available_steps==2 and pf.missing_steps==1
    assert pf.locked_revision_id==project.locked_revision_id


def test_run_stores_gaps_metrics_snapshots_revisions_and_no_permit_verdict(tmp_path):
    project,store,h=fixture(tmp_path)
    run=run_history(project,store,h,evaluator=evaluator,max_steps=3,now=datetime(2026,10,9,tzinfo=timezone.utc))
    assert run.manifest['stage']=='COMPLETED'
    assert run.summary['solved_steps']==2 and run.summary['missing_steps']==1
    assert run.summary['section_peak_delta_T_C']['max']==12.
    assert run.summary['permit_verdict'] is None
    assert run.manifest['source']['original_time_varying_descriptors']==ORIGINAL
    assert run.manifest['source']['locked_design_descriptors']!=ORIGINAL
    assert run.manifest['criteria']['legal_pass_fail'] is None
    rows=json.loads((run.path/'timestep_metrics.json').read_text())['rows']
    assert [r['status'] for r in rows]==['SOLVED','MISSING','SOLVED']
    assert rows[1]['missing']==['source.flow_m3h']
    assert rows[0]['section_peak_delta_T_C']==6.
    assert rows[-1]['section_peak_delta_T_C']==12.
    assert len(h.calls)==2
    assert load_historical_run(project,run.run_id).summary==run.summary
    assert (run.path/'config.normalized.json').is_file()
    assert (run.path/'timestep_metrics.csv').is_file()


def test_bounded_run_does_not_claim_full_period_when_truncated(tmp_path):
    p,s,h=fixture(tmp_path)
    run=run_history(p,s,h,evaluator=evaluator,max_steps=1)
    assert run.summary['selected_steps']==1
    assert not run.summary['complete_historical_period']
    assert run.summary['missing_steps']==0


def test_rejects_invalid_bound_or_unlock_or_stale_revision(tmp_path):
    p,s,h=fixture(tmp_path)
    with pytest.raises(WorkspaceError,match='max_steps'):
        run_history(p,s,h,evaluator=evaluator,max_steps=0)
    unlocked=replace(p,locked_revision_id=None)
    with pytest.raises(WorkspaceError,match='locked'):
        restored_forcing_config(unlocked,s)


def test_fail_closed_manifest_never_masquerades_as_completed(tmp_path):
    p,s,h=fixture(tmp_path)
    def bad(*args,**kwargs):raise RuntimeError('solver failure')
    with pytest.raises(RuntimeError,match='solver failure'):
        run_history(p,s,h,evaluator=bad,max_steps=1)
    directories=list((p.project_dir/'runs').iterdir())
    assert len(directories)==1
    manifest=json.loads((directories[0]/'manifest.json').read_text())
    assert manifest['stage']=='FAILED' and manifest['error_type']=='RuntimeError'
    with pytest.raises(WorkspaceError,match='not completed'):
        load_historical_run(p,directories[0].name)


def test_no_matching_history_original_source_blocks_run(tmp_path):
    p,s,h=fixture(tmp_path)
    def different(cfg):
        raise ProviderDataError('plant source differs')
    h._require_config=different
    with pytest.raises(ProviderDataError,match='plant source differs'):
        preflight_history(p,s,h)


def test_nonfinite_model_metrics_mark_run_failed(tmp_path):
    p,s,h=fixture(tmp_path)
    def invalid(*args,**kwargs):return SimpleNamespace(metrics={'section_peak_delta_T_C':float('nan'),
                         'plan_peak_delta_T_C':1.,'final_bulk_dilution':1.})
    with pytest.raises(ProviderDataError,match='nonfinite'):
        run_history(p,s,h,evaluator=invalid,max_steps=1)
    d=list((p.project_dir/'runs').iterdir())[0]
    assert json.loads((d/'manifest.json').read_text())['stage']=='FAILED'


def test_artifact_integrity_invalidates_tampered_result(tmp_path):
    p,s,h=fixture(tmp_path)
    run=run_history(p,s,h,evaluator=evaluator,max_steps=1)
    assert len(run.manifest['artifact_sha256'])==4
    f=run.path/'timestep_metrics.csv'
    f.write_text(f.read_text()+'\n# tampered',encoding='utf-8')
    with pytest.raises(WorkspaceError,match='bytes changed'):
        load_historical_run(p,run.run_id)
