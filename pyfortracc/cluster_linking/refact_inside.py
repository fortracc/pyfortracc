import numpy as np

def refact_inside(cur_frme):
    """
    This function refact uids for the inside clusters.
    The conditions to new uids are:
    - threshold_level is 0
    - inside_idx is not null

    Parameters
    ----------
    cur_frme : pandas.DataFrame
    Current frame.

    Returns
    -------
    cur_frme : pandas.DataFrame
    Current frame with new uids.
    """
    # Rules:
    # Get threshold_level 0 of clusters with inside_idx
    thr_lvl = 'threshold_level'
    ins_idx = 'inside_idx'
    base_thld = cur_frme[(cur_frme[thr_lvl] == 0) &
                        (cur_frme[ins_idx].notnull())].index
    # Get inside clusters of the new clusters
    insd = cur_frme.loc[base_thld][[ins_idx, 'uid']].dropna()
    insd = insd.explode(ins_idx).set_index(ins_idx)
    # Get current uid of the inside clusters
    insd['cur_iud'] = cur_frme.loc[insd.index, 'uid'].values
    insd['cur_iud'] = insd['cur_iud'].fillna(0)
    # Set difference between current uid and inside clusters
    insd['diff'] = (insd['cur_iud'].astype(int) - insd['uid']).abs()
    # Select only differences greater than 1
    insd = insd[insd['diff'] >= 1]
    iuid_thrls = cur_frme.loc[insd.index, thr_lvl].values
    insd[thr_lvl] = iuid_thrls
    insd['iuid'] = insd['uid'].astype(int)
    insd[thr_lvl] = insd[thr_lvl] - 1
    insd[thr_lvl] = insd[thr_lvl].astype(str)
    insd[thr_lvl] = insd[thr_lvl].apply(lambda x: '0' * int(x) +
                                        str(np.random.randint(1, 999)))
    insd['iuid'] = insd['iuid'].astype(str) + '.' + insd[thr_lvl]
    insd['iuid'] = insd['iuid'].astype(float)
    cur_frme.loc[insd.index, 'uid'] = insd['iuid'].astype(int).values
    cur_frme.loc[insd.index, 'iuid'] = insd['iuid'].values
    return cur_frme
