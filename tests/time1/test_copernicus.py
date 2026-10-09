from __future__ import annotations
import sys, types
from datetime import datetime
from pathlib import Path
import numpy as np
import pytest
xr = pytest.importorskip("xarray", reason="Copernicus synthetic xarray adapter test requires ocean extra")
from plume.errors import ProviderDataError,ConfigError
from plume.providers.base import ProviderContext
from plume.providers.copernicus import (CopernicusProvider,_normalise_depth_profile,
                                         _timestamp,_haversine_km)

SITE={"latitude_deg":60.,"longitude_deg":5.,"water_depth_m":20.}
CLOCK={"start":"2025-01-01T00:00:00Z","end":"2025-01-04T00:00:00Z","step":"P1D"}
CTX=ProviderContext(config_dir=Path('/tmp'),site=SITE,clock=CLOCK)


def dataset(*,dry=True,units='degrees_C',depths=(.5,5.,25.),temp='thetao'):
    times=np.array(['2025-01-01','2025-01-02','2025-01-03'],dtype='datetime64[s]')
    shape=(3,len(depths),2,2)
    sea=np.full(shape,12.0)
    sal=np.full(shape,35.0)
    u=np.full(shape,.2)
    v=np.full(shape,-.03)
    sea[1,...]=np.nan
    sal[1,...]=np.nan
    u[1,...]=np.nan
    v[1,...]=np.nan
    if dry:
        for a in (sea,sal,u,v):a[:,:,0,0]=np.nan
    d=xr.Dataset({temp:(('time','depth','latitude','longitude'),sea,{'units':units,'standard_name':'sea_water_potential_temperature'}),
                  'so':(('time','depth','latitude','longitude'),sal,{'units':'1e-3','standard_name':'sea_water_salinity'}),
                  'uo':(('time','depth','latitude','longitude'),u,{'units':'m s-1'}),
                  'vo':(('time','depth','latitude','longitude'),v,{'units':'m s-1'})},
                 coords={'time':times,'depth':list(depths),'latitude':[60.,60.001],'longitude':[5.,5.001]},
                 attrs={'title':'Synthetic Copernicus fixture','cmems_product_id':'test-physical-product'})
    return d


def spec(role,**other):
    basic={'provider':'copernicus','role':role,'dataset_id':'synthetic-gridded'}
    if role=='temperature': basic['temperature_kind']='potential_pt0'
    if role in ('temperature','salinity'): basic['salinity_kind']='practical'
    basic.update(other)
    if role == 'temperature' and basic.get('temperature_kind') == 'in_situ_ITS90' and 'salinity_kind' not in other:
        basic.pop('salinity_kind',None)
    return CopernicusProvider().normalize_spec(basic,context='forcing.ambient.'+{'temperature':'temperature_profile_C','salinity':'salinity_profile_psu','current':'current_profile'}[role])


def test_units_and_provider_role_require_explicit_semantics():
    with pytest.raises(ConfigError,match='temperature_kind'):
        spec('temperature',temperature_kind='K')
    with pytest.raises(ConfigError,match='role'):
        CopernicusProvider().normalize_spec({'provider':'copernicus','role':'salinity','dataset_id':'x'},context='forcing.ambient.current_profile')
    with pytest.raises(ConfigError,match='unsupported'):
        spec('salinity',password='do-not-commit')


def test_nearest_wet_fallback_and_native_masked_hour(monkeypatch):
    import plume.providers.copernicus as c
    monkeypatch.setattr(c,'_open_dataset',lambda **kwargs:dataset())
    out=c.CopernicusProvider().load(spec('salinity'),context=CTX)
    assert out.data_kind=='time_depth_profile'
    assert [r['time'] for r in out.records if r['depth_m']==0.]==['2025-01-01T00:00:00Z','2025-01-03T00:00:00Z']
    assert out.records[0]['value']==35.
    assert any('selected wet cell' in w for w in out.provenance.warnings)
    assert any('Top wet level' in w for w in out.provenance.warnings)
    assert out.provenance.request['actual_latitude_deg']==60.
    assert out.provenance.request['actual_longitude_deg']==5.001
    assert out.provenance.input_sha256


def test_current_vectors_are_not_magnitudes(monkeypatch):
    import plume.providers.copernicus as c
    monkeypatch.setattr(c,'_open_dataset',lambda **kwargs:dataset())
    out=c.CopernicusProvider().load(spec('current'),context=CTX)
    assert out.data_kind=='time_depth_vector'
    assert out.records[0]['u_east_mps']==.2 and out.records[0]['v_north_mps']==-.03
    assert out.records[0]['depth_m']==0.
    assert out.records[-1]['depth_m']==20.


def test_potential_temperature_converted_via_gsw_not_relabelled(monkeypatch):
    import plume.providers.copernicus as c
    calls=[]
    class FakeGSW:
        def p_from_z(self,z,lat): calls.append('pressure');return -z
        def SA_from_SP(self,sp,p,lon,lat): calls.append('SA');return sp+.2
        def CT_from_pt(self,sa,pt): calls.append('CT');return pt+.4
        def t_from_CT(self,sa,ct,p): calls.append('t');return ct+.3
    monkeypatch.setitem(sys.modules,'gsw',FakeGSW())
    monkeypatch.setattr(c,'_open_dataset',lambda **kwargs:dataset())
    result=c.CopernicusProvider().load(spec('temperature',salinity_variable='so'),context=CTX)
    assert calls==['pressure','SA','CT','t','pressure','SA','CT','t']
    assert result.records[0]['value']==pytest.approx(12.7)
    assert result.provenance.request['conversion'].startswith('potential_pt0')


def test_rejects_wrong_temperature_units_or_metadata(monkeypatch):
    import plume.providers.copernicus as c
    monkeypatch.setattr(c,'_open_dataset',lambda **kwargs:dataset(units='K'))
    with pytest.raises(ProviderDataError,match='unit'):
        c.CopernicusProvider().load(spec('temperature'),context=CTX)
    wrong=dataset();wrong['thetao'].attrs['standard_name']='sea_water_temperature'
    monkeypatch.setattr(c,'_open_dataset',lambda **kwargs:wrong)
    with pytest.raises(ProviderDataError,match='metadata'):
        c.CopernicusProvider().load(spec('temperature'),context=CTX)


def test_land_only_or_too_far_fallback_fails(monkeypatch):
    import plume.providers.copernicus as c
    land=dataset(dry=False)
    for key in land.data_vars:land[key].values[:]=np.nan
    monkeypatch.setattr(c,'_open_dataset',lambda **kwargs:land)
    with pytest.raises(ProviderDataError,match='No full-depth wet'):
        c.CopernicusProvider().load(spec('salinity'),context=CTX)
    monkeypatch.setattr(c,'_open_dataset',lambda **kwargs:dataset())
    with pytest.raises(ProviderDataError,match='No full-depth wet'):
        c.CopernicusProvider().load(spec('salinity',max_fallback_km=0.),context=CTX)


def test_shallow_dataset_cannot_invent_seabed(monkeypatch):
    import plume.providers.copernicus as c
    monkeypatch.setattr(c,'_open_dataset',lambda **kwargs:dataset(depths=(.5, 5., 17.)))
    with pytest.raises(ProviderDataError,match='full water column'):
        c.CopernicusProvider().load(spec('salinity'),context=CTX)


def test_subsecond_time_and_physical_depth_rules():
    with pytest.raises(ProviderDataError,match='exact UTC second'):
        _timestamp(np.datetime64('2025-01-01T00:00:00.500'))
    with pytest.raises(ProviderDataError,match='surface wet level'):
        _normalise_depth_profile(np.array([1.8,5,25]),np.array([1,2,3]),
                                  seabed_m=20,surface_hold_limit_m=1.)
    with pytest.raises(ProviderDataError,match='no bottom extrapolation'):
        _normalise_depth_profile(np.array([.5,5,15]),np.array([1,2,3]),
                                  seabed_m=20,surface_hold_limit_m=1.)


def test_no_credentials_in_request(monkeypatch):
    import plume.providers.copernicus as c
    captured=[]
    monkeypatch.setattr(c,'_open_dataset',lambda **kwargs:(captured.append(kwargs),dataset())[1])
    out=c.CopernicusProvider().load(spec('salinity'),context=CTX)
    assert not {'username','password','token'} & set(captured[0])
    assert 'synthetic-gridded'==out.provenance.source


def test_correct_haversine_distance_of_exact_grid_site():
    assert _haversine_km(60.,5.,60.,5.)==0.
    assert .04<_haversine_km(60.,5.,60.,5.001)<.07


def test_salinity_requires_explicit_quantity_semantics():
    with pytest.raises(ConfigError, match='salinity_kind'):
        spec('salinity',salinity_kind='absolute')
    with pytest.raises(ConfigError, match='salinity_kind'):
        spec('temperature',salinity_kind='unspecified')

def test_salinity_absolute_metadata_rejected(monkeypatch):
    import plume.providers.copernicus as c
    d=dataset(); d['so'].attrs['standard_name']='sea_water_absolute_salinity'
    monkeypatch.setattr(c,'_open_dataset',lambda **kw:d)
    with pytest.raises(ProviderDataError, match='not Practical'):
        c.CopernicusProvider().load(spec('salinity'),context=CTX)


def test_split_thetao_is_never_silently_relabelled_without_paired_salinity(monkeypatch):
    import plume.providers.copernicus as c
    only_thetao=dataset()[['thetao']]
    monkeypatch.setattr(c,'_open_dataset',lambda **kw:only_thetao)
    result=c.CopernicusProvider().load(spec('temperature'),context=CTX)
    assert result.data_kind=='time_depth_potential'
    assert result.records[0]['value']==12.
    assert result.provenance.request['conversion'].startswith('DEFERRED_')
    assert result.provenance.request['variables']==['thetao']


def test_normalized_copernicus_descriptors_can_be_re_normalized_from_saved_project():
    adapter=CopernicusProvider()
    for role in ('temperature','salinity','current'):
        raw=spec(role)
        context='forcing.ambient.'+{'temperature':'temperature_profile_C','salinity':'salinity_profile_psu','current':'current_profile'}[role]
        assert adapter.normalize_spec(raw,context=context)==raw
    combo=spec('temperature',salinity_variable='so')
    assert adapter.normalize_spec(combo,context='forcing.ambient.temperature_profile_C')==combo


def test_deep_native_levels_below_requested_seabed_do_not_falsely_reject_wet_cell(monkeypatch):
    """Coastal cell may be 26m wet but downloaded 40m grid contains NaN below 26m."""
    import plume.providers.copernicus as c
    ds = dataset(dry=False, depths=(.5,5.,25.,35.,45.))
    ds['so'].values[:, 3:, :, :] = np.nan
    monkeypatch.setattr(c, '_open_dataset', lambda **kw: ds)
    out = c.CopernicusProvider().load(spec('salinity'), context=CTX)
    assert out.records[-1]['depth_m'] == SITE['water_depth_m']
    assert out.provenance.request['native_levels_m'] == [.5,5.,25.]
    assert out.provenance.request['downloaded_native_levels_m'] == [.5,5.,25.,35.,45.]


def test_config_cannot_override_potential_temperature_as_in_situ(monkeypatch):
    import plume.providers.copernicus as c
    native = dataset()
    monkeypatch.setattr(c, '_open_dataset', lambda **kw: native)
    with pytest.raises(ProviderDataError, match='native temperature metadata is not in-situ'):
        c.CopernicusProvider().load(spec('temperature', temperature_kind='in_situ_ITS90'), context=CTX)
    truly_insitu = dataset()
    truly_insitu['thetao'].attrs['standard_name'] = 'sea_water_temperature'
    monkeypatch.setattr(c, '_open_dataset', lambda **kw: truly_insitu)
    out = c.CopernicusProvider().load(spec('temperature', temperature_kind='in_situ_ITS90'), context=CTX)
    assert out.data_kind == 'time_depth_profile'
    assert out.records[0]['value'] == 12.


def test_role_specific_copernicus_options_are_never_silently_dropped():
    with pytest.raises(ConfigError, match='incompatible'):
        spec('current', variable='thetao')
    with pytest.raises(ConfigError, match='incompatible'):
        spec('salinity', temperature_kind='potential_pt0')
    with pytest.raises(ConfigError, match='ignored salinity conversion'):
        spec('temperature', temperature_kind='in_situ_ITS90', salinity_variable='so')
