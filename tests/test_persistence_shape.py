"""Tests of the persistence forecast: every system must be moved rigidly, keeping its shape, size and rain rates."""
import numpy as np
import pandas as pd
import pytest

from pyfortracc.forecast.persistence import persistence

NY, NX, RES = 40, 60, 0.1
NAME_LIST = dict(thresholds=[0.1, 1, 5], y_dim=NY, x_dim=NX, x_res=RES, y_res=RES,
                 lat_min=-2.0, lat_max=2.0, lon_min=-3.0, lon_max=3.0, edges=False)


def rows(timestamp, level, uid, iuid, ys, xs, values, u_pix, v_pix):
    """One cluster of a tracking table: pixel arrays and the vector in degrees per time step."""
    return dict(timestamp=pd.Timestamp(timestamp), threshold_level=level, uid=float(uid),
                iuid=np.nan if iuid is None else float(iuid), array_y=np.asarray(ys), array_x=np.asarray(xs),
                array_values=np.asarray(values, float), u_=u_pix * RES, v_=v_pix * RES)


def nested_system(t, u_out, v_out, u_core, v_core, y0=15, x0=20, uid=1):
    """A system with nested thresholds: 0.1 mm/h block 8 x 10 px (0.5 mm/h), 1 mm/h block 4 x 4 inside (2 mm/h),
    5 mm/h block 2 x 2 inside it (8 mm/h). Every threshold carries its own vector."""
    field = np.full((NY, NX), np.nan)
    field[y0:y0 + 8, x0:x0 + 10] = 0.5
    field[y0 + 2:y0 + 6, x0 + 3:x0 + 7] = 2.0
    field[y0 + 3:y0 + 5, x0 + 4:x0 + 6] = 8.0
    out = []
    for level, thr, uu, vv, iuid in [(0, 0.1, u_out, v_out, None), (1, 1, u_core, v_core, uid + 0.1),
                                     (2, 5, u_core, v_core, uid + 0.01)]:
        ys, xs = np.nonzero(field >= thr)
        out.append(rows(t, level, uid, iuid, ys, xs, field[ys, xs], uu, vv))
    return field, out


def write(tmp_path, frames):
    files = []
    for i, frame in enumerate(frames):
        f = tmp_path / f'{i}.parquet'
        pd.DataFrame(frame).to_parquet(f)
        files.append(str(f))
    return files


def shifted(field, dy, dx):
    out = np.full_like(field, np.nan)
    ys, xs = np.nonzero(np.isfinite(field))
    out[ys + dy, xs + dx] = field[ys, xs]
    return out


def test_nested_system_moves_rigidly(tmp_path):
    """The cores have vectors different from the system's: the forecast must still be the whole system shifted by the
    system's vector (no copies of the cores, the same area at every threshold)."""
    _, prev = nested_system('2020-01-01 00:00', 3, 1, 1, 2, x0=17, y0=14)
    field, last = nested_system('2020-01-01 00:30', 3, 1, 1, 2)
    fc = persistence(write(tmp_path, [prev, last]), NAME_LIST)
    expected = shifted(field, 1, 3)
    assert np.array_equal(np.isfinite(fc), np.isfinite(expected))
    assert np.allclose(fc[np.isfinite(fc)], expected[np.isfinite(expected)])
    for thr in NAME_LIST['thresholds']:
        assert np.count_nonzero(fc >= thr) == np.count_nonzero(field >= thr)


def test_half_pixel_shift_is_rigid(tmp_path):
    """A mean displacement of exactly half a pixel moves every pixel by the same whole number of pixels."""
    _, prev = nested_system('2020-01-01 00:00', 0, 0, 0, 0)
    field, last = nested_system('2020-01-01 00:30', 1, 0, 1, 0)      # window mean u = 0.5 px
    fc = persistence(write(tmp_path, [prev, last]), NAME_LIST)
    assert np.count_nonzero(np.isfinite(fc)) == np.count_nonzero(np.isfinite(field))
    for dx in (0, 1):
        if np.array_equal(np.isfinite(fc), np.isfinite(shifted(field, 0, dx))):
            break
    else:
        pytest.fail('the system was deformed by the rounding of a half-pixel shift')


def test_overlap_keeps_the_larger_value(tmp_path):
    """Two systems moved onto the same pixels: each keeps its rain above its thresholds (no mean of the two)."""
    _, prev_a = nested_system('2020-01-01 00:00', 0, 0, 0, 0, x0=10, uid=1)
    _, prev_b = nested_system('2020-01-01 00:00', 0, 0, 0, 0, x0=20, uid=2)
    fa, last_a = nested_system('2020-01-01 00:30', 4, 0, 4, 0, x0=10, uid=1)
    fb, last_b = nested_system('2020-01-01 00:30', -4, 0, -4, 0, x0=20, uid=2)
    fc = persistence(write(tmp_path, [prev_a + prev_b, last_a + last_b]), NAME_LIST)
    sa, sb = shifted(fa, 0, 2), shifted(fb, 0, -2)                    # window means: +2 and -2 px
    assert np.count_nonzero(np.isfinite(sa) & np.isfinite(sb)) > 0      # they do overlap
    expected = np.fmax(sa, sb)
    assert np.array_equal(np.isfinite(fc), np.isfinite(expected))
    assert np.allclose(fc[np.isfinite(fc)], expected[np.isfinite(expected)])


def test_edges_wrap_the_longitude(tmp_path):
    """With edges=True (global grid) a system leaving the east edge comes back on the west edge, whole."""
    nl = dict(NAME_LIST, edges=True)
    _, prev = nested_system('2020-01-01 00:00', 6, 0, 6, 0, x0=45)
    field, last = nested_system('2020-01-01 00:30', 6, 0, 6, 0, x0=48)
    fc = persistence(write(tmp_path, [prev, last]), nl)
    ys, xs = np.nonzero(np.isfinite(field))
    expected = np.full_like(field, np.nan)
    expected[ys, (xs + 6) % NX] = field[ys, xs]
    assert np.array_equal(np.isfinite(fc), np.isfinite(expected))
    assert np.allclose(fc[np.isfinite(fc)], expected[np.isfinite(expected)])


def test_without_edges_pixels_leave_the_grid(tmp_path):
    """Without edges the pixels moved out of the grid are dropped (not piled on the border)."""
    _, prev = nested_system('2020-01-01 00:00', 6, 0, 6, 0, x0=45)
    field, last = nested_system('2020-01-01 00:30', 6, 0, 6, 0, x0=48)
    fc = persistence(write(tmp_path, [prev, last]), NAME_LIST)
    ys, xs = np.nonzero(np.isfinite(field))
    inside = xs + 6 < NX
    assert np.count_nonzero(np.isfinite(fc)) == inside.sum()
    assert np.count_nonzero(np.isfinite(fc[:, -1])) == np.count_nonzero(ys[xs + 6 == NX - 1] >= 0)


def test_orphan_inner_cluster_moves_with_its_own_vector(tmp_path):
    """An inner cluster with no first-threshold cluster around it (the outer one was below the minimum size) is still
    forecast, with its own vector."""
    core = np.zeros((NY, NX), bool)
    core[5:8, 5:8] = True
    ys, xs = np.nonzero(core)
    prev = [rows('2020-01-01 00:00', 1, 9, 9.1, ys, xs - 2, np.full(9, 3.0), 2, 0)]
    last = [rows('2020-01-01 00:30', 1, 9, 9.1, ys, xs, np.full(9, 3.0), 2, 0)]
    fc = persistence(write(tmp_path, [prev, last]), NAME_LIST)
    assert np.array_equal(np.argwhere(np.isfinite(fc)), np.argwhere(np.roll(core, 2, axis=1)))
