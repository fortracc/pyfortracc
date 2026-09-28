def iuid_suffix(iuid):
    """
    Return the integer after the decimal point of an iuid.

    The iuid of an inner cluster is written as '<uid>.<zeros><n>', where the
    number of zeros is threshold_level - 1. The zeros are dropped by int(),
    so the result is n.

    Parameters
    ----------
    iuid : float
        Inner uid.

    Returns
    -------
    int
        The suffix n, or 0 if the iuid has no decimal part.
    """
    text = repr(float(iuid))
    if '.' not in text or 'e' in text:
        return 0
    return int(text.split('.')[1])


def count_iuids(frame, iuid_cnt=None):
    """
    Update the iuid counters with the iuids of a linked frame.

    The counter of each (uid, threshold_level) is the largest suffix already
    used by that uid at that level, so the next inner cluster gets a suffix
    that was never used. Only the uids of the frame are kept: a uid missing
    from a frame is never linked again, so its counters are no longer needed.

    Parameters
    ----------
    frame : pandas.DataFrame
        Linked frame with the uid, iuid and threshold_level columns.
    iuid_cnt : dict, optional
        Counters {(uid, threshold_level): suffix} to be updated.

    Returns
    -------
    dict
        The updated counters.
    """
    iuid_cnt = dict(iuid_cnt) if iuid_cnt else {}
    if frame.empty or 'uid' not in frame.columns:
        return {}
    alive = set(frame['uid'].dropna().astype(int))
    iuid_cnt = {key: n for key, n in iuid_cnt.items() if key[0] in alive}
    if 'iuid' not in frame.columns:
        return iuid_cnt
    inner = frame.loc[frame['iuid'].notnull() &
                      (frame['threshold_level'] > 0),
                      ['iuid', 'threshold_level']]
    for iuid, level in zip(inner['iuid'].values,
                           inner['threshold_level'].values):
        key = (int(iuid), int(level))
        iuid_cnt[key] = max(iuid_cnt.get(key, 0), iuid_suffix(iuid))
    return iuid_cnt


def next_iuids(uids, levels, iuid_cnt):
    """
    Create deterministic iuids for new inner clusters.

    The suffix is the next value of the (uid, threshold_level) counter.
    Suffixes ending in 0 are skipped, because the trailing zero would be lost
    in the float and the iuid would collide with a shorter suffix
    (e.g. 5.10 == 5.1).

    Parameters
    ----------
    uids : array-like of int
        Uid of each inner cluster.
    levels : array-like of int
        Threshold level of each inner cluster (greater than 0).
    iuid_cnt : dict
        Counters {(uid, threshold_level): suffix}, updated in place.

    Returns
    -------
    list of float
        The iuid of each inner cluster.
    """
    iuids = []
    for uid, level in zip(uids, levels):
        key = (int(uid), int(level))
        suffix = iuid_cnt.get(key, 0) + 1
        if suffix % 10 == 0:
            suffix += 1
        iuid_cnt[key] = suffix
        iuids.append(float('{}.{}{}'.format(key[0], '0' * (key[1] - 1),
                                            suffix)))
    return iuids

