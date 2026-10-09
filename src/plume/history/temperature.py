"""TIME-1B paired-source ocean temperature normalization via official GSW.

Copernicus thetao is potential temperature referenced to 0 dbar. Paired SP
must be from the exact timestamp and a spatially coherent wet cell. Never
reinterpret pt0 as in-situ ITS-90 without a deliberate conversion.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from ..errors import ProviderDataError


def paired_pt0_to_insitu(
    potential_profile: Sequence[tuple[float,float]],
    practical_salinity_profile: Sequence[tuple[float,float]],
    *, latitude_deg: float, longitude_deg: float,
) -> tuple[tuple[float,float], ...]:
    """Apply TEOS-10 to one exact-hour profile, interpolating SP in *depth only*."""
    if len(potential_profile)<2 or len(practical_salinity_profile)<2:
        raise ProviderDataError("paired potential temperature needs full vertical thetao and SP columns")
    temp_depth=np.array([x[0] for x in potential_profile],dtype=float)
    pt=np.array([x[1] for x in potential_profile],dtype=float)
    sal_depth=np.array([x[0] for x in practical_salinity_profile],dtype=float)
    sp=np.array([x[1] for x in practical_salinity_profile],dtype=float)
    if (not np.isfinite(temp_depth).all() or not np.isfinite(pt).all() or
        not np.isfinite(sal_depth).all() or not np.isfinite(sp).all() or
        np.any(np.diff(temp_depth)<=0) or np.any(np.diff(sal_depth)<=0) or
        np.any(sp<0) or temp_depth[0] < sal_depth[0]-1e-8 or
        temp_depth[-1] > sal_depth[-1]+1e-8):
        raise ProviderDataError("potential T and Practical Salinity columns must be finite, ordered and depth-coincident in coverage")
    sp_at_temp=np.interp(temp_depth,sal_depth,sp)
    try:
        import gsw
    except ImportError as exc:
        raise ProviderDataError("official GSW-Python is required for thetao (pt0) → in-situ ITS-90 conversion") from exc
    try:
        pressure=gsw.p_from_z(-temp_depth,latitude_deg)
        absolute=gsw.SA_from_SP(sp_at_temp,pressure,longitude_deg,latitude_deg)
        conservative=gsw.CT_from_pt(absolute,pt)
        in_situ=np.asarray(gsw.t_from_CT(absolute,conservative,pressure),dtype=float)
    except (ValueError,TypeError,FloatingPointError) as exc:
        raise ProviderDataError("paired TEOS-10 temperature conversion failed") from exc
    if in_situ.shape != temp_depth.shape or not np.isfinite(in_situ).all():
        raise ProviderDataError("paired TEOS-10 temperature conversion produced invalid values")
    return tuple((float(d),float(v)) for d,v in zip(temp_depth,in_situ))
