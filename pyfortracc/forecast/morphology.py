import numpy as np
import pandas as pd
from scipy.ndimage import distance_transform_edt, gaussian_filter
from pyfortracc.utilities.utils import set_operator

# Settings of the trends of the persistence forecast (name_list['morph_trend']).
# They are fixed on purpose, so the user only switches the trends on or off.
# Maximum change of the area per time step: the rate is clipped to
# [1 / (1 + MAX_RATE), 1 + MAX_RATE]
MAX_RATE = 0.5
# Damping of the trends with the lead time: at the n-th lead time (n = 0 for the
# first one) they are multiplied by DAMPING ** n, since a growth or a decay does
# not last for ever (tuned on GOES-19 IR, tests/forecast_goes19.py)
DAMPING = 0.6
# Smoothing (pixels) of the border of the dilated/eroded systems; the values of
# the new pixels are averaged over twice this radius
SIGMA = 1.0


def system_trends(track_df, name_list):
    """
    Area and intensity trends of each cluster over the observation window.

    Only the steps where the cluster continues (status CON, one delta_time apart)
    are used: in a merge or a split the area jumps without the system growing, and
    a cluster touching the border of the domain shrinks because it leaves the grid.
    The area trend is the mean log of the size ratios of these steps (clipped to
    +- log(1 + MAX_RATE)) and the intensity trend the mean change of the mean value
    per step.

    Parameters
    ----------
    track_df : pd.DataFrame
        Tracking tables of the observation window, uid being the identity of the
        cluster at its threshold level.
    name_list : dict
        The parameters of the tracking (delta_time).

    Returns
    -------
    pd.DataFrame
        threshold_level, uid, log_rate (log of the area ratio per step),
        value_delta and the extremes of the values observed in the window
        (value_min, value_max).
    """
    cols = ['threshold_level', 'uid', 'timestamp', 'status', 'size', 'mean', 'min', 'max']
    df = track_df[[c for c in cols if c in track_df.columns]].copy()
    df['board'] = track_df['board'].fillna(False).astype(bool) if 'board' in track_df.columns else False
    df = df.dropna(subset=['uid']).sort_values(['threshold_level', 'uid', 'timestamp'])
    grp = df.groupby(['threshold_level', 'uid'])
    step = ((grp['timestamp'].diff() == pd.to_timedelta(name_list['delta_time'], unit='m')) &
            (df['status'] == 'CON') & ~df['board'] & ~grp['board'].shift(fill_value=True))
    df['log_rate'] = np.log(df['size'] / grp['size'].shift()).where(step)
    df['value_delta'] = grp['mean'].diff().where(step)
    trends = df.groupby(['threshold_level', 'uid']).agg(
        log_rate=('log_rate', 'mean'),
        value_delta=('value_delta', 'mean'),
        value_min=('min', 'min'),
        value_max=('max', 'max')).reset_index()
    # Symmetric in log: growing by 1 + max_rate or shrinking by the inverse
    max_log = np.log1p(MAX_RATE)
    trends['log_rate'] = np.clip(trends['log_rate'].fillna(0), -max_log, max_log)
    trends['value_delta'] = trends['value_delta'].fillna(0)
    return trends


def pixel_levels(values, thresholds, operator):
    """Index of the highest threshold each value satisfies (-1 for none)."""
    op = set_operator(operator)
    return op(values[:, None], np.asarray(thresholds, float)[None, :]).sum(axis=1) - 1


def level_bounds(levels, thresholds, operator, value_min, value_max):
    """
    Range of the values that keep each pixel at its threshold level: between its
    threshold and the next one (excluded), and up to the extreme observed in the
    window at the last level. Works for both orderings ('>' with increasing
    thresholds, e.g. reflectivity, and '<' with decreasing ones, e.g. brightness
    temperature).
    """
    thr = np.append(np.asarray(thresholds, float), np.nan)
    cur, nxt = thr[levels], thr[levels + 1]
    last = np.isnan(nxt)
    if operator.startswith('>'):
        low = np.nextafter(cur, np.inf) if operator == '>' else cur
        high = np.where(last, max(value_max, np.nanmax(cur)),
                        nxt if operator == '>' else np.nextafter(nxt, -np.inf))
    else:
        high = np.nextafter(cur, -np.inf) if operator == '<' else cur
        low = np.where(last, min(value_min, np.nanmin(cur)),
                       nxt if operator == '<' else np.nextafter(nxt, np.inf))
    return low, high


def border_score(mask, sigma):
    """
    Signed distance to the border of a mask (positive inside), smoothed by a
    Gaussian of sigma pixels. Taking the pixels of highest score grows or shrinks
    the mask evenly along its whole border, and the smoothing rounds the new border
    (no ragged edges, thin spikes or one-pixel holes). Being a positive linear
    filter it keeps the order of nested masks: if A is inside B, score(A) <= score(B).
    """
    sdf = distance_transform_edt(mask) - distance_transform_edt(~mask)
    return gaussian_filter(sdf, sigma) if sigma > 0 else sdf


def morph_cluster(xs, ys, values, base, log_rate, value_delta, value_min, value_max, thresholds, operator):
    """
    Dilate (log_rate > 0) or erode (log_rate < 0) a cluster, with the clusters of
    the higher thresholds inside it, so that its area becomes exp(log_rate) times
    the current one, and shift its values by value_delta.

    The pixels are added (removed) in the order of their smoothed signed distance to
    the border (border_score, SIGMA), which grows or shrinks the cluster evenly
    along its whole border with a smooth outline, and exactly the number of pixels
    given by the rate is taken. A dilation always contains the cluster and an
    erosion is always inside it. The same score level is applied to every threshold
    level, which keeps the inner clusters nested in the outer ones (the cores grow
    and shrink with the system and vanish when eroded away).

    No mean of the system is written: a pixel that changed level takes a local
    average of the values of its new level only (fill_values), so every pixel stays
    in its class and no spurious core is created (a mean over the system would cross
    the thresholds of a multi-threshold system, and has no meaning for categorical
    fields). The original pixels keep their observed values. The values are then
    shifted by value_delta (the trend of the mean of the system) but clipped to the
    range of their threshold level, so the intensity changes without moving the
    borders, which are set by the dilation/erosion only.

    Returns
    -------
    (np.ndarray, np.ndarray, np.ndarray)
        array_x, array_y and array_values of the new cluster, in grid pixels (they
        may lie outside the grid; the shift drops or wraps them).
    """
    sigma = SIGMA
    n = len(xs)
    target = int(np.floor(n * np.exp(log_rate) + 0.5))
    if target == n and value_delta == 0:
        return xs, ys, values
    # Local window around the cluster, wide enough for the dilation: the
    # dilation of any set by the radius of a disc of the target area covers it
    pad = int(np.ceil(np.sqrt(max(target, n) / np.pi) + 3 * sigma)) + 2
    x0, y0 = xs.min() - pad, ys.min() - pad
    shape = (ys.max() - y0 + pad + 1, xs.max() - x0 + pad + 1)
    lev = np.full(shape, -1, dtype=np.int64)
    val = np.full(shape, np.nan)
    lev[ys - y0, xs - x0] = np.maximum(pixel_levels(values, thresholds, operator), base)
    val[ys - y0, xs - x0] = values
    levels = range(base, lev.max() + 1)

    new_lev = lev.copy()
    if target != n:
        score = {k: border_score(lev >= k, sigma) for k in levels}
        mask = lev >= base
        # Exactly the number of pixels of the rate at the base level, taken by
        # rank (ties of symmetric shapes broken by position); the inner levels
        # grow or shrink down/up to the same score
        if target > n:
            # Add the outside pixels of highest score
            cand = np.flatnonzero(~mask)
            pick = cand[np.argsort(-score[base].ravel()[cand], kind='stable')[:target - n]]
            cut = score[base].ravel()[pick].min()
            inside = {k: (lev >= k) | (score[k] >= cut) for k in levels}
            inside[base] = mask.copy()
        else:
            # Keep the inside pixels of highest score
            cand = np.flatnonzero(mask)
            pick = cand[np.argsort(-score[base].ravel()[cand], kind='stable')[:target]]
            cut = score[base].ravel()[pick].min() if target > 0 else np.inf
            inside = {k: (lev >= k) & (score[k] >= cut) for k in levels}
            inside[base] = np.zeros_like(mask)
        inside[base].ravel()[pick] = True
        # Every level stays inside the level below it
        for k in levels[1:]:
            inside[k] &= inside[k - 1]
        new_lev = np.where(inside[base], base - 1 + sum(inside[k].astype(np.int64) for k in levels), -1)
        fill_values(val, lev, new_lev, levels, 2 * max(sigma, 1))
    ny, nx = np.nonzero(new_lev >= base)
    new_values = val[ny, nx] + value_delta
    low, high = level_bounds(new_lev[ny, nx], thresholds, operator, value_min, value_max)
    new_values = np.clip(new_values, low, high)
    return nx + x0, ny + y0, new_values


def fill_values(val, lev, new_lev, levels, sigma):
    """
    Values of the pixels that changed level (in place): the nearest original pixel
    of the new level, then averaged with a Gaussian over the pixels of that level
    (original ones included as anchors, kept unchanged), which avoids the patches of
    constant value of a large dilation. Only values of the same level are combined.
    """
    for k in levels:
        changed = (new_lev == k) & (lev != k)
        if not changed.any():
            continue
        ring = lev == k if (lev == k).any() else lev >= k
        _, (iy, ix) = distance_transform_edt(~ring, return_indices=True)
        filled = np.where(changed, val[iy, ix], val)
        region = (new_lev == k).astype(float)
        num = gaussian_filter(np.nan_to_num(filled) * region, sigma)
        den = gaussian_filter(region, sigma)
        with np.errstate(invalid='ignore', divide='ignore'):
            smooth = num / den
        filled = np.where(changed & (den > 0), smooth, filled)
        val[changed] = filled[changed]


def apply_trends(clusters, history_df, name_list, lead=0):
    """
    Replace the pixels of the clusters to be moved by the persistence with their
    dilated/eroded version and their values shifted by the intensity trend, both
    taken from the history of each cluster in the observed window. The trends are
    damped with the lead time: at the lead time `lead` (0 for the first one) they
    are multiplied by DAMPING ** lead, since a growth or a decay does not last for
    ever. Clusters without history keep their shape and values.
    """
    if clusters.empty or name_list['operator'] in ('==', '!='):
        # Categorical thresholds are not nested: there is no ordering to grow
        # or shrink the classes, nor an intensity to extrapolate
        return clusters
    trends = system_trends(history_df, name_list)
    damping = DAMPING ** lead
    trends['log_rate'] *= damping
    trends['value_delta'] *= damping
    clusters = clusters.merge(trends, on=['threshold_level', 'uid'], how='left')
    clusters['log_rate'] = clusters['log_rate'].fillna(0.0)
    clusters['value_delta'] = clusters['value_delta'].fillna(0.0)
    return morph_clusters(clusters, name_list)


def morph_clusters(clusters, name_list):
    """
    Dilate/erode each cluster by its log_rate and shift its values by its
    value_delta (columns of clusters, see morph_cluster), the values kept between
    value_min and value_max at the last threshold level (NaN: the extremes of the
    cluster). Clusters eroded away are dropped.
    """
    new_x, new_y, new_v = [], [], []
    for row in clusters.itertuples():
        xs, ys, vs = morph_cluster(np.asarray(row.array_x, dtype=np.int64),
                                   np.asarray(row.array_y, dtype=np.int64),
                                   np.asarray(row.array_values, dtype=float),
                                   int(row.threshold_level), row.log_rate, row.value_delta,
                                   np.nanmin(row.array_values) if pd.isna(row.value_min) else row.value_min,
                                   np.nanmax(row.array_values) if pd.isna(row.value_max) else row.value_max,
                                   name_list['thresholds'], name_list['operator'])
        new_x.append(xs)
        new_y.append(ys)
        new_v.append(vs)
    clusters['array_x'], clusters['array_y'], clusters['array_values'] = new_x, new_y, new_v
    return clusters[clusters['array_x'].map(len) > 0]
