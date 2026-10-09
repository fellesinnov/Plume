import sys
import pytest
from plume.errors import ProviderDataError
from plume.history.temperature import paired_pt0_to_insitu


def test_pt0_to_in_situ_exact_hour_paired_sp_gsw_calls(monkeypatch):
    calls=[]
    class GSW:
        def p_from_z(self,z,lat):calls.append('p');return -z
        def SA_from_SP(self,sp,p,lon,lat):calls.append('SA');return sp+0.2
        def CT_from_pt(self,sa,pt):calls.append('CT');return pt+0.3
        def t_from_CT(self,sa,ct,p):calls.append('t');return ct+0.4
    monkeypatch.setitem(sys.modules,'gsw',GSW())
    result=paired_pt0_to_insitu(((0.,10.),(10.,9.),(20.,8.)),
                                ((0.,34.),(20.,35.)),latitude_deg=60.,longitude_deg=5.)
    assert calls==['p','SA','CT','t']
    assert [x[0] for x in result]==[0.,10.,20.]
    assert [x[1] for x in result]==pytest.approx([10.7,9.7,8.7])


def test_unpaired_or_unbounded_depth_is_not_silently_converted():
    with pytest.raises(ProviderDataError,match='depth-coincident'):
        paired_pt0_to_insitu(((0.,10.),(20.,8.)),((1.,35.),(15.,36.)),
                             latitude_deg=60.,longitude_deg=5.)
    with pytest.raises(ProviderDataError,match='finite'):
        paired_pt0_to_insitu(((0.,10.),(20.,8.)),((0.,-1.),(20.,35.)),
                             latitude_deg=60.,longitude_deg=5.)
