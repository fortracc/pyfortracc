import numpy as np
import pandas as pd
from .iuid_counter import next_iuids


def refact_inside(cur_frme, uid_iter, iuid_cnt=None):
    """
    This function refact uids for the inside clusters.
    The conditions to new uids are:
    - threshold_level is 0
    - inside_idx is not null

    The iuids of the new inner clusters are deterministic: the suffix is the
    next value of the (uid, threshold_level) counter in iuid_cnt, so it never
    repeats an iuid already used by the same uid.

    Parameters
    ----------
    cur_frme : pandas.DataFrame
    Current frame.
    uid_iter : int
    Next free uid.
    iuid_cnt : dict, optional
    Counters {(uid, threshold_level): suffix}, updated in place.

    Returns
    -------
    cur_frme : pandas.DataFrame
    Current frame with new uids.
    """
    if iuid_cnt is None:
        iuid_cnt = {}
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
    # Sorted and unique so the iuids do not depend on the row order
    insd = insd[~insd.index.duplicated(keep='last')].sort_index()
    if not insd.empty:
        uids = insd['uid'].values.astype(int)
        levels = cur_frme.loc[insd.index, thr_lvl].values.astype(int)
        cur_frme.loc[insd.index, 'uid'] = uids
        cur_frme.loc[insd.index, 'iuid'] = next_iuids(uids, levels, iuid_cnt)
    # Clusters still without uid receive new uids
    null_uid = cur_frme.loc[cur_frme['uid'].isnull()].index
    if len(null_uid) > 0:
        max_uid = cur_frme['uid'].max()
        if not pd.isnull(max_uid):
            uid_iter = max(uid_iter, int(max_uid) + 1)
        uids = np.arange(uid_iter, uid_iter + len(null_uid), 1, dtype=int)
        cur_frme.loc[null_uid, 'uid'] = uids
        levels = cur_frme.loc[null_uid, thr_lvl].values.astype(int)
        inner = levels > 0
        if inner.any():
            cur_frme.loc[null_uid[inner], 'iuid'] = next_iuids(
                uids[inner], levels[inner], iuid_cnt)
    return cur_frme
