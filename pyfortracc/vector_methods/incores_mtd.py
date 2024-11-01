import numpy as np
from pyfortracc.utilities.math_utils import calc_mean_uv

def innercores_mtd(cur_base, cur_inner, cur_bse_idx, cur_ins_idx):
    """
    This method receives only events of that have inner cores and creates a new vector based on the inner cores' spatial components.

    Parameters
    ----------
    cur_base : DataFrame
        current frame base cells
    cur_inner : DataFrame
        previous frame inner cells
    cur_bse_idx : array
        array of indexes of current base cells
    cur_ins_idx : array
        array of indexes of current inner cells
    
    Returns
    -------
    u_ : list
        list of zonal (u) components
    v_ : list
        list of meridional (v) components
    
    Notes
    -------
    u : float
        The zonal component, representing the east-west direction (zonal).
    v : float
        The meridional component, representing the north-south direction (meridional).
    """
    # Set output
    u_, v_ = [], []
    # Loop over cur_inned_idx
    for cidx in range(len(cur_bse_idx)):
        cur_bse_uv = cur_base.loc[cur_bse_idx[cidx]][['u_','v_']].values
        cur_inn_uv = cur_inner.loc[cur_ins_idx[cidx]][['u_','v_']]
        cur_inn_uv = cur_inn_uv.dropna(axis=0).values
        # if len(cur_inn_uv) == 0:
        #     continue
        uv_list = np.vstack((cur_bse_uv, cur_inn_uv))
        # Calculate mean of vectors
        mean_uv = calc_mean_uv(uv_list)
        u_.append(mean_uv[0])
        v_.append(mean_uv[1])
    return u_, v_