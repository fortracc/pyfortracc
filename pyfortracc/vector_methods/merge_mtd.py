import numpy as np
from scipy import stats
from pyfortracc.utilities.math_utils import uv_components, calc_addition_uv


def merge_mtd(cur_mrg_df, prv_mrg_df, cur_mrgs_idx, prv_mrg_idx):
    """ 
    This method receive only events of Merge and create a new vector for merged cells.
    The vector as created between mean of vectors of previous cells.
    
    Parameters
    ----------
    cur_mrg_df: DataFrame
        current frame
    prev_mrg_df: DataFrame
        previous frame
    cur_mrgs_idx: array
        array of indexes of merged cells
    prv_mrg_idx: array 
        array of indexes of previous merged cells
    
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
    # Transform prv_mrg_idx to list of events before merge
    prv_mrg_idx = prv_mrg_idx.tolist()
    # Loop over cur_mrg_idx
    for cidx in range(len(cur_mrgs_idx)):
        cur_crtd = cur_mrg_df.loc[cur_mrgs_idx[cidx]]['centroid']
        prv_crtds = prv_mrg_df.loc[prv_mrg_idx[cidx]]['centroid'].values
        uv_comps = np.array([uv_components(p.coords[0], cur_crtd.coords[0])
                    for p in prv_crtds])
        # Calculate adding of vectors
        mean_uv = calc_addition_uv(uv_comps)
        u_.append(mean_uv[0])
        v_.append(mean_uv[1])    
    return u_, v_