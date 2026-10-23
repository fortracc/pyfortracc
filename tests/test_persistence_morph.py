"""Tests of the trends of the persistence forecast (morph_trend): dilation/erosion and intensity trend of the systems."""
import numpy as np
import pandas as pd

from pyfortracc.forecast.persistence import persistence
from pyfortracc.forecast import morphology
from pyfortracc.forecast.morphology import pixel_levels

NY, NX, RES = 60, 80, 0.1
NAME_LIST = dict(thresholds=[20, 30, 40], operator='>=', delta_time=10, y_dim=NY, x_dim=NX, x_res=RES,
                 y_res=RES, lat_min=-3.0, lat_max=3.0, lon_min=-4.0, lon_max=4.0, edges=False,
                 morph_trend=False)


def disc_system(radius, cy=30, cx=40, values=(25, 35, 45), offset=0.0):
    """A system of nested discs: radius (level 0), radius / 2 (level 1) and radius / 4 (level 2)."""
    yy, xx = np.mgrid[:NY, :NX]
    r = np.hypot(yy - cy, xx - cx)
    field = np.full((NY, NX), np.nan)
    field[r <= radius] = values[0] + offset
    field[r <= radius / 2] = values[1] + offset
    field[r <= radius / 4] = values[2] + offset
    return field


def frame(t, field, status, thresholds=NAME_LIST['thresholds'], operator='>=', uid=1, u_pix=0):
    """The rows of one system (all its thresholds) in a tracking table."""
    out = []
    for level, thr in enumerate(thresholds):
        mask = (field >= thr) if operator.startswith('>') else (field <= thr)
        ys, xs = np.nonzero(mask & np.isfinite(field))
        if not len(ys):
            continue
        vals = field[ys, xs]
        out.append(dict(timestamp=pd.Timestamp(t), threshold_level=level, uid=float(uid),
                        iuid=np.nan if level == 0 else uid + level / 10, status=status, board=False,
                        size=float(len(ys)), mean=vals.mean(), min=vals.min(), max=vals.max(),
                        array_y=ys, array_x=xs, array_values=vals, u_=u_pix * RES, v_=0.0))
    return out


def write(tmp_path, frames):
    files = []
    for i, f in enumerate(frames):
        path = tmp_path / f'{i}.parquet'
        pd.DataFrame(f).to_parquet(path)
        files.append(str(path))
    return files


def growing(tmp_path, radii, status='CON', **kw):
    frames = [frame(f'2020-01-01 00:{10 * i:02d}', disc_system(r, **kw), 'NEW' if i == 0 else status)
              for i, r in enumerate(radii)]
    return write(tmp_path, frames), disc_system(radii[-1], **kw)


def test_disabled_is_plain_persistence(tmp_path):
    files, last = growing(tmp_path, [6, 8, 10])
    fc = persistence(files, NAME_LIST)
    assert np.array_equal(np.isfinite(fc), np.isfinite(last))


def test_growing_system_is_dilated_by_its_rate(tmp_path):
    """Area history 8 -> 9 -> 10 px radius: the forecast area is the last area times the mean growth rate, also for a
    slow growth that adds only part of the first ring of pixels around the system."""
    for radii in ([8, 9, 10], [10, 10.3, 10.6]):
        files, last = growing(tmp_path, radii)
        sizes = [np.count_nonzero(np.isfinite(disc_system(r))) for r in radii]
        rate = np.sqrt(sizes[2] / sizes[0])
        fc = persistence(files, dict(NAME_LIST, morph_trend=True))
        assert abs(np.count_nonzero(np.isfinite(fc)) - sizes[2] * rate) <= 1
        assert np.all(np.isfinite(fc[np.isfinite(last)]))             # dilation contains the system


def test_decaying_system_is_eroded(tmp_path):
    files, last = growing(tmp_path, [12, 10, 8])
    fc = persistence(files, dict(NAME_LIST, morph_trend=True))
    assert 0 < np.count_nonzero(np.isfinite(fc)) < np.count_nonzero(np.isfinite(last))
    assert np.all(np.isfinite(last[np.isfinite(fc)]))                 # erosion is inside the system


def test_thresholds_stay_nested_and_values_stay_in_class(tmp_path):
    """Every new pixel gets a local average of the values of its own threshold class (no mean of the system, no fake
    cores), and the values of a class stay inside it."""
    yy, xx = np.mgrid[:NY, :NX]
    frames, last = [], None
    for i, r in enumerate([6, 9, 12]):
        field = disc_system(r)
        field[np.isfinite(field)] += (xx[np.isfinite(field)] % 3) * 0.9   # texture inside each class
        frames.append(frame(f'2020-01-01 00:{10 * i:02d}', field, 'NEW' if i == 0 else 'CON'))
        last = field
    fc = persistence(write(tmp_path, frames), dict(NAME_LIST, morph_trend=True))
    assert np.any(np.isfinite(fc) & ~np.isfinite(last))
    # Each core grows too and remains inside the level below it
    for thr in NAME_LIST['thresholds']:
        assert np.count_nonzero(fc >= thr) > np.count_nonzero(last >= thr)
    # Every pixel of a class has a value inside that class and within the values of that class in the system
    vals = fc[np.isfinite(fc)]
    lev = pixel_levels(vals, NAME_LIST['thresholds'], '>=')
    assert lev.min() == 0
    last_vals = last[np.isfinite(last)]
    last_lev = pixel_levels(last_vals, NAME_LIST['thresholds'], '>=')
    for k, (lo, hi) in enumerate([(20, 30), (30, 40), (40, np.inf)]):
        observed = last_vals[last_lev == k]
        assert np.all((vals[lev == k] >= max(lo, observed.min() - 1)) & (vals[lev == k] < hi))


def test_border_is_smooth(tmp_path):
    """A ragged system (a disc with a jagged border) is dilated and eroded with a smooth border: no holes, no isolated
    pixels, a single piece."""
    from scipy.ndimage import binary_fill_holes, label
    yy, xx = np.mgrid[:NY, :NX]
    theta = np.arctan2(yy - 30, xx - 40)
    for radii in ([8, 10, 12], [14, 12, 10]):
        frames = []
        for i, r in enumerate(radii):
            field = disc_system(r * (1 + 0.15 * np.sign(np.sin(9 * theta))))
            frames.append(frame(f'2020-01-01 00:{10 * i:02d}', field, 'NEW' if i == 0 else 'CON'))
        fc = persistence(write(tmp_path, frames), dict(NAME_LIST, morph_trend=True))
        mask = np.isfinite(fc)
        assert np.array_equal(binary_fill_holes(mask), mask)
        assert label(mask)[1] == 1


def test_trends_are_damped_with_the_lead_time(tmp_path, monkeypatch):
    """At the n-th lead time the area rate is rate ** (DAMPING ** n), from the observed history."""
    files, last = growing(tmp_path, [8, 9, 10])
    sizes = [np.count_nonzero(np.isfinite(disc_system(r))) for r in (8, 9, 10)]
    rate = np.sqrt(sizes[2] / sizes[0])
    for lead, damping in [(2, 0.5), (3, 1.0)]:
        monkeypatch.setattr(morphology, 'DAMPING', damping)
        fc = persistence(files, dict(NAME_LIST, morph_trend=True), lead=lead, history_files=files)
        assert abs(np.count_nonzero(np.isfinite(fc)) - sizes[2] * rate ** (damping ** lead)) <= 1


def test_trends_come_from_the_history_files(tmp_path):
    """The forecast passes the observed window as history: a frame without history (only the last one) still gets
    the observed trend."""
    files, last = growing(tmp_path, [8, 9, 10])
    sizes = [np.count_nonzero(np.isfinite(disc_system(r))) for r in (8, 9, 10)]
    fc = persistence(files[-1:], dict(NAME_LIST, morph_trend=True), history_files=files)
    assert abs(np.count_nonzero(np.isfinite(fc)) - sizes[2] * np.sqrt(sizes[2] / sizes[0])) <= 1


def test_merge_steps_are_ignored(tmp_path):
    """A jump of area at a merge (status MRG) is not a growth of the system."""
    files, last = growing(tmp_path, [6, 12], status='MRG')
    fc = persistence(files, dict(NAME_LIST, morph_trend=True))
    assert np.array_equal(np.isfinite(fc), np.isfinite(last))


def test_rate_is_clipped(tmp_path, monkeypatch):
    monkeypatch.setattr(morphology, 'MAX_RATE', 0.2)
    files, last = growing(tmp_path, [3, 12])
    fc = persistence(files, dict(NAME_LIST, morph_trend=True))
    assert np.count_nonzero(np.isfinite(fc)) <= 1.2 * np.count_nonzero(np.isfinite(last)) + 1


def test_values_follow_the_trend_inside_their_class(tmp_path):
    """Values rise by the trend of the mean but never cross a threshold nor exceed the observed maximum."""
    frames = [frame('2020-01-01 00:00', disc_system(10, offset=0), 'NEW'),
              frame('2020-01-01 00:10', disc_system(10, offset=3), 'CON')]
    last = disc_system(10, offset=3)
    fc = persistence(write(tmp_path, frames), dict(NAME_LIST, morph_trend=True))
    assert np.array_equal(np.isfinite(fc), np.isfinite(last))         # same area: the borders are not moved
    for thr in NAME_LIST['thresholds']:
        assert np.count_nonzero(fc >= thr) == np.count_nonzero(last >= thr)
    assert np.nanmax(fc) <= np.nanmax(last)
    assert np.nanmean(fc) > np.nanmean(last)


def test_brightness_temperature_operator(tmp_path):
    """'<=' with decreasing thresholds (e.g. IR brightness temperature in K): a cooling, growing system."""
    thr = [235, 220, 210]
    nl = dict(NAME_LIST, thresholds=thr, operator='<=', morph_trend=True)
    kw = dict(values=(230, 215, 200))
    frames = [frame(f'2020-01-01 00:{10 * i:02d}', disc_system(r, offset=-i, **kw), 'NEW' if i == 0 else 'CON',
                    thresholds=thr, operator='<=') for i, r in enumerate([6, 8, 10])]
    last = disc_system(10, offset=-2, **kw)
    fc = persistence(write(tmp_path, frames), nl)
    assert np.count_nonzero(np.isfinite(fc)) > np.count_nonzero(np.isfinite(last))
    for t in thr:
        assert np.count_nonzero(fc <= t) > np.count_nonzero(last <= t)
    assert np.nanmax(fc) <= 235 and np.nanmin(fc) >= np.nanmin(last)
