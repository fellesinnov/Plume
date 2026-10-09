from types import SimpleNamespace
import numpy as np
import pytest
from plume.errors import ProviderDataError
from plume.ocean import history_panel, render_ocean_panel

TIMES=('2025-01-01T00:00:00Z','2025-01-01T01:00:00Z','2025-01-01T02:00:00Z')

def history():
    values={
        'ambient.temperature_profile_C':{'data_kind':'time_depth_profile','records_by_time':{
            TIMES[0]:[{'depth_m':0.,'value':10.},{'depth_m':20.,'value':6.}],
            TIMES[2]:[{'depth_m':0.,'value':13.},{'depth_m':20.,'value':8.}],
        }},
        'ambient.salinity_profile_psu':{'data_kind':'depth_profile','records':[
            {'depth_m':0.,'value':34.},{'depth_m':20.,'value':35.}]},
        'ambient.current_profile':{'data_kind':'vector_constant','records':[
            {'u_east_mps':.15,'v_north_mps':-.1}]}}
    return SimpleNamespace(verify_identity=lambda:None,request={'site':{'water_depth_m':20.}},
                           series=values,clock_times=TIMES,data_sha256='a'*64)

def test_temperature_plot_never_interpolates_absent_hour():
    p=history_panel(history(),quantity='temperature',depth_samples=11)
    assert p.values.shape==(11,3)
    assert p.missing_columns==(1,)
    assert np.isnan(p.values[:,1]).all()
    assert p.values[0,0]==10 and p.values[-1,2]==8
    assert p.values[5,0]==8 and p.values[5,2]==10.5

def test_static_current_does_not_claim_shear():
    p=history_panel(history(),quantity='u_east',depth_samples=8)
    assert np.allclose(p.values,.15)
    assert p.missing_columns==()

def test_ambient_salinity_units_visible():
    p=history_panel(history(),quantity='salinity')
    assert p.units=='PSU'
    assert p.values[0,0]==34.

def test_invalid_history_plot_quantity_fails():
    with pytest.raises(ProviderDataError,match='unknown historical view'):
        history_panel(history(),quantity='chlorophyll')
    with pytest.raises(ProviderDataError,match='resolution'):
        history_panel(history(),depth_samples=1)

def test_standalone_real_matplotlib_history_png(tmp_path):
    panel=history_panel(history(),quantity='temperature')
    fig=render_ocean_panel(panel,selected=TIMES[2])
    try:
        outfile=tmp_path/'ocean.png'
        fig.savefig(outfile,dpi=100)
        assert outfile.stat().st_size>10000
        assert 'not a thermal plume result' in fig.axes[0].get_title()
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)


def test_potential_temperature_is_not_labeled_in_situ_before_pinning():
    h=history()
    h.series['ambient.temperature_profile_C']['data_kind']='time_depth_potential'
    assert 'Potential temperature' in history_panel(h).name
