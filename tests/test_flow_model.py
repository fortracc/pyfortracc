"""Tests of the residual flow matching forecast (forecast_mode 'flow'): field encoding, inputs, generation and
the untrained model, which forecasts the persistence with the trends of the window."""
import numpy as np
import pandas as pd
import pytest

flow_model = pytest.importorskip('pyfortracc.forecast.flow_model')
from pyfortracc.forecast.persistence import persistence

NY, NX, RES = 40, 48, 0.1
NAME_LIST = dict(thresholds=[235, 210], operator='<=', delta_time=10, y_dim=NY, x_dim=NX, x_res=RES, y_res=RES,
                 lat_min=-2.0, lat_max=2.0, lon_min=-2.4, lon_max=2.4, edges=False, morph_trend=True)


def system(radius, cy=20, cx=24):
    """A cold system: 230 K inside radius, 200 K inside radius / 2 (the 210 K core)."""
    yy, xx = np.mgrid[:NY, :NX]
    r = np.hypot(yy - cy, xx - cx)
    field = np.full((NY, NX), np.nan)
    field[r <= radius] = 230.0
    field[r <= radius / 2] = 200.0
    return field


def frame(t, field, status, u_pix=1):
    rows = []
    for level, thr in enumerate(NAME_LIST['thresholds']):
        ys, xs = np.nonzero(np.isfinite(field) & (field <= thr))
        vals = field[ys, xs]
        rows.append(dict(timestamp=pd.Timestamp(t), threshold_level=level, uid=1.0, status=status, board=False,
                         size=float(len(ys)), lifetime=0.0, mean=vals.mean(), min=vals.min(), max=vals.max(),
                         std=vals.std(), array_y=ys, array_x=xs, array_values=vals, u_=u_pix * RES, v_=0.0))
    return rows


def window_files(tmp_path):
    """Three frames of a growing system moving one pixel per step to the east."""
    files = []
    for k, (radius, status) in enumerate([(6, 'NEW'), (7, 'CON'), (8, 'CON')]):
        t = pd.Timestamp('2025-11-05 12:00') + pd.Timedelta(minutes=10 * k)
        path = tmp_path / f'{t:%Y%m%d_%H%M}.parquet'
        pd.DataFrame(frame(t, system(radius, cx=24 + k), status)).to_parquet(path)
        files.append(str(path))
    return files


def test_encode_decode_roundtrip():
    image = system(8)
    field = flow_model.encode(image, NAME_LIST, scale=10.0)
    assert np.all(field[np.isnan(image)] == flow_model.OUTSIDE)
    assert np.all(field[np.isfinite(image)] >= 0)
    back = flow_model.decode(field, NAME_LIST, scale=10.0)
    assert np.array_equal(np.isfinite(back), np.isfinite(image))
    assert np.allclose(back[np.isfinite(image)], image[np.isfinite(image)], atol=1e-3)


def test_probability_matched_mean_keeps_the_values():
    rng = np.random.default_rng(0)
    members = rng.normal(size=(8, 10, 12)).astype(np.float32)
    pmm = flow_model.probability_matched_mean(members)
    assert pmm.shape == (10, 12)
    # The ranks of the mean, the values of the members
    assert np.array_equal(np.argsort(pmm.ravel()), np.argsort(members.mean(0).ravel(), kind='stable'))
    assert pmm.min() >= members.min() and pmm.max() <= members.max()


def test_conditions_channels(tmp_path):
    files = window_files(tmp_path)
    frames, _ = flow_model.frames_of(files, NAME_LIST, [])
    table = flow_model.map_table(pd.concat(frames, ignore_index=True), NAME_LIST, [], 3)
    columns = list(flow_model.MAPS)
    mean, std = np.zeros(len(columns)), np.ones(len(columns))
    maps = flow_model.normalized_maps(table, columns, mean, std)
    label = flow_model.labels(frames[-1], flow_model.step_rows(frames[-1], table), NAME_LIST)
    # The core pixels get the step of the 210 K cluster
    core = system(8, cx=26) <= 210
    assert set(table.loc[np.unique(label[core]), 'threshold_level']) == {1}
    assert np.all(label[np.isnan(system(8, cx=26))] == -1)
    base = flow_model.encode(system(8, cx=27), NAME_LIST, 10.0)
    context = [flow_model.encode(flow_model.frame_image(f, NAME_LIST), NAME_LIST, 10.0) for f in frames[::-1]]
    cond = flow_model.conditions(base, context, label, flow_model.optical_flow(frames[-1], NAME_LIST), maps,
                                 columns, mean, std)
    assert cond.shape == (len(flow_model.CHANNELS) - 1, NY, NX)
    # Without opt_field the optical flow channels are the mean vector of the cluster (1 pixel per step)
    iu = 1 + flow_model.CONTEXT + len(columns)
    assert np.allclose(cond[iu][label >= 0], 1.0)
    assert np.all(cond[iu][label < 0] == 0)


def test_untrained_model_is_the_persistence_with_trends(tmp_path):
    files = window_files(tmp_path)
    model = flow_model.FlowUNet(len(flow_model.CHANNELS) - 1, base=16).eval()
    frames, _ = flow_model.frames_of(files, NAME_LIST, [])
    window_df = pd.concat(frames, ignore_index=True)
    base = flow_model.base_image(window_df, window_df, NAME_LIST)
    # The base is the persistence forecast with morph_trend
    assert np.array_equal(np.isfinite(base), np.isfinite(persistence(files, NAME_LIST)))
    cond = np.zeros((len(flow_model.CHANNELS) - 1, NY, NX), np.float32)
    residual = flow_model.probability_matched_mean(flow_model.generate(model, cond, 'cpu'))
    assert residual.shape == (NY, NX) and np.all(residual == 0)
    field = flow_model.encode(base, NAME_LIST, 10.0)
    image = flow_model.decode(field + residual, NAME_LIST, 10.0)
    assert np.array_equal(np.isfinite(image), np.isfinite(base))
    assert np.allclose(image[np.isfinite(base)], base[np.isfinite(base)], atol=1e-3)


def test_rollout_inputs_read_the_generated_frames():
    n, size = 4, 8
    data = dict(field=np.zeros((n, size, size), np.float16), label=np.full((n, size, size), -1, np.int32),
                flow=np.full((n, 2, size, size), np.nan, np.float16), base=np.ones((n, size, size), np.float16))
    samples = [(i, [i, i - 1, -1]) for i in range(n - 1)]
    chain = flow_model.chains(samples, 2)[0]
    assert [item[0] for item in chain] == [0, 1]
    columns = list(flow_model.MAPS)
    maps = np.zeros((1, len(columns)), np.float32)
    mean, std = np.zeros(len(columns)), np.ones(len(columns))
    generated = [np.full((size, size), 2.0, np.float32)]   # the frame 1 generated from the frame 0
    cond, target, weight, base = flow_model.sample_inputs(data, maps, columns, mean, std, chain, 0, 0, size,
                                                         generated)
    # The base of frame 1 carries the error of the generated frame 1 (2 - 0); its context is that frame
    assert np.all(base == 3.0) and np.all(cond[1] == 2.0) and np.all(cond[2] == 0.0)
    assert np.all(target == -3.0)
