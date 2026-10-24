"""
Comparison of the forecast modes on one week of GOES-19 infrared (ABI channel 13, brightness temperature)
convective systems over Mato Grosso do Sul / Mato Grosso, Brazil: persistence, persistence + morph_trend,
the LSTM and the residual flow matching model (forecast_mode 'flow').

The days 2025-11-01 to 2025-11-09 are downloaded with goesgcp (https://github.com/helvecioneto/goesgcp) and
tracked with two thresholds (235 K and 210 K). The learned models are trained on the week of TRAIN_PERIOD
(2025-11-01 to 2025-11-07) and forecast the next day, from every hour of ANCHORS, 6 hours ahead (the
observations of 2025-11-09 verify the last leads). The flow
model is used in the two ways of the learned modes:
    - flow: pyfortracc.forecast trains it at the first anchor (name_list['rnn_train_period']), saves it in
      output_path/forecast/models/ and reuses it at the next anchors;
    - flow_weights: pyfortracc.forecast.flow_model.train_model trains it (here it finds the model saved by
      the first one, with the same settings) and returns its path, given to the forecasts in
      name_list['rnn_weights'] (inference only).
No observation after an anchor is used to forecast from it. Writes, in output_goes19_flow/:
    - forecast_<tag>/: the forecasts of each one; forecast/models/: the trained models
    - forecast_flow_scores.csv and forecast_flow_scores.png: POD, FAR, CSI and area bias per lead time
    - forecast_flow_comparison_<anchor>.png: observed and each forecast at +10 min, +1 h, +3 h and +6 h

Needs PyTorch and goesgcp (pip install torch goesgcp). Run from the tests directory:
python forecast_flow_goes19.py (python forecast_flow_goes19.py plots only redraws the figures).
"""
import glob
import os
import shutil
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append('../')
import pyfortracc
import forecast_goes19 as base
from forecast_goes19 import read_function, scores

DAYS_START, DAYS_END = '2025-11-01 00:00:00', '2025-11-09 23:50:00'   # days downloaded and tracked
TRAIN_PERIOD = ['2025-11-01 00:00:00', '2025-11-07 23:50:00']          # rnn_train_period: one week
ANCHORS = pd.date_range('2025-11-08 12:00', '2025-11-08 22:00', freq='1h')   # forecast_time of each forecast
INPUT = 'input_goes19_flow/'
OUTPUT = 'output_goes19_flow/'

# Set the parameters
name_list = {}
name_list['input_path'] = INPUT # path to the input data
name_list['output_path'] = OUTPUT # path to the output data (tracking, forecasts and trained models)
name_list['timestamp_pattern'] = base.PATTERN + '.nc' # timestamp file pattern: goes19_ch13_%Y%m%d_%H%M.nc
name_list['thresholds'] = [235, 210] # brightness temperature (K): cloud shield, deep convection
name_list['min_cluster_size'] = [30, 5] # in number of pixels (~4.4 km) per cluster
name_list['operator'] = '<=' # colder than the thresholds
name_list['delta_time'] = 10 # in minutes
name_list['min_overlap'] = 10 # Minimum overlap between clusters in percentage

# Not mandatory parameters, if not set, the algorithm will use the default values
name_list['spl_correction'] = True # Set to True to apply the Split correction
name_list['mrg_correction'] = True # Set to True to apply the Merge correction
name_list['inc_correction'] = True # Set to True to apply the Inner Cores correction
name_list['opt_correction'] = True # Optical Flow correction: its vector field is also an input of the flow model
name_list['new_correction'] = True # NEW clusters (also in the forecast frames) get the neighbours' vector
name_list['edges'] = False # If True, the edges of the clusters will be considered in the tracking

# Optional parameters, if not set, the algorithm will not use geospatial information
name_list['lon_min'] = -60.004908820693196 # Min longitude of data in degrees (outer edge of the grid)
name_list['lon_max'] = -45.96490882069319 # Max longitude of data in degrees
name_list['lat_min'] = -24.022779820396284 # Min latitude of data in degrees
name_list['lat_max'] = -11.982779820396285 # Max latitude of data in degrees

# Forecast parameters
name_list['forecast_time'] = str(ANCHORS[0]) # Overwritten by the loop over the ANCHORS below
name_list['observation_window'] = 6 # Number of previous images (60 min) of the persistence (mean vector and trends)
name_list['lead_time'] = 36 # Amount of time steps to forecast (6 hours)
name_list['forecast_mode'] = 'persistence' # 'persistence', 'lstm', 'gru' or 'flow' (each forecast below sets its own)
name_list['morph_trend'] = False # Persistence only: dilate/erode the systems by their area trend

# Learned forecast parameters (forecast_mode 'lstm', 'gru' or 'flow')
name_list['rnn_weights'] = None # None: train the model (saved in output_path/forecast/models/);
                                # a path to a .pt file: use that trained model, for inference only
name_list['rnn_train_period'] = TRAIN_PERIOD # the week the models are trained on
name_list['rnn_aux'] = [] # extra columns of the tracking table used by the model, e.g. ['land_use']
name_list['rnn_arch'] = None # None: default architecture; a dict to change it (see the modules)

# The test compares five forecasts, each run by pyfortracc.forecast with a copy of the name_list above in
# which only the forecast parameters written below change.
FORECASTS = {}

# 1. Persistence: each system is moved by its mean vector over the observation_window, keeping its shape
name_list_persistence = dict(name_list)
FORECASTS['persistence'] = name_list_persistence

# 2. Persistence + morph_trend: the systems also grow or decay by their trends over the observation_window
name_list_morph_trend = dict(name_list)
name_list_morph_trend['morph_trend'] = True
FORECASTS['morph_trend'] = name_list_morph_trend

# 3. LSTM trained on the week (at the first anchor, then reused from output_path/forecast/models/)
name_list_lstm = dict(name_list)
name_list_lstm['forecast_mode'] = 'lstm'
FORECASTS['lstm'] = name_list_lstm

# 4. Flow matching trained on the week by pyfortracc.forecast (at the first anchor, then reused)
name_list_flow = dict(name_list)
name_list_flow['forecast_mode'] = 'flow'
FORECASTS['flow'] = name_list_flow

# 5. The same flow model given by its weights: pyfortracc.forecast.flow_model.train_model returns the path of
#    the model (trained, or reused when one with the same settings exists), set in rnn_weights in run()
name_list_flow_weights = dict(name_list)
name_list_flow_weights['forecast_mode'] = 'flow'
FORECASTS['flow_weights'] = name_list_flow_weights

LABELS = {'persistence': 'Persistence', 'morph_trend': 'Persistence + morph_trend', 'lstm': 'LSTM (week)',
          'flow': 'Flow matching (week)', 'flow_weights': 'Flow matching (rnn_weights)'}
COLORS = {'persistence': 'tab:blue', 'morph_trend': 'tab:red', 'lstm': 'tab:green', 'flow': 'tab:purple',
          'flow_weights': 'tab:orange'}


def download():
    """Download and crop the GOES-19 images of the days with goesgcp (skipped when they are already there)."""
    os.makedirs(INPUT, exist_ok=True)
    # The day of forecast_rnn_goes19.py, when it was already downloaded
    for path in glob.glob('input_goes19_rnn/*.nc'):
        if not os.path.exists(INPUT + os.path.basename(path)):
            shutil.copy(path, INPUT)
    expected = len(pd.date_range(DAYS_START, DAYS_END, freq='10min'))
    if len(glob.glob(INPUT + '*.nc')) >= expected:
        return
    # See forecast_goes19.download_goes19 for the rioxarray import and the PROJ variables. The parallel
    # mode of goesgcp may end without writing the files, so each day is downloaded sequentially, the days
    # in parallel processes, each in its own directory (goesgcp works in and removes ./tmp/)
    code = 'import sys, rioxarray\nfrom goesgcp.main import main\nsys.argv = sys.argv[1:]\nmain()'
    env = {k: v for k, v in os.environ.items() if k not in ('PROJ_DATA', 'PROJ_LIB')}
    jobs = []
    for day in pd.date_range(DAYS_START, DAYS_END, freq='1D'):
        end = day + pd.Timedelta('23h50min')
        if len(glob.glob(INPUT + f'*{day:%Y%m%d}_*.nc')) >= 144:
            continue
        workdir = os.path.abspath(f'download_{day:%Y%m%d}/')
        os.makedirs(workdir, exist_ok=True)
        args = ['goesgcp', '--satellite', base.SATELLITE, '--product', base.PRODUCT, '--channel',
                str(base.CHANNEL), '--var_name', 'CMI', '--start', str(day), '--end', str(end),
                '--freq', '10 min', '--resolution', str(base.RESOLUTION), '--output', os.path.abspath(INPUT) + '/',
                '--file_pattern', base.PATTERN, '--parallel', 'False']
        for key, value in base.BOX.items():
            args += [f'--{key}', str(value)]
        jobs.append((workdir, subprocess.Popen([sys.executable, '-c', code] + args, env=env, cwd=workdir)))
    failed = [job.wait() for _, job in jobs]
    for workdir, _ in jobs:
        shutil.rmtree(workdir, ignore_errors=True)
    if any(failed):
        raise RuntimeError('goesgcp failed to download some of the days.')


def forecast_image(tag, anchor, lead):
    t = anchor + pd.Timedelta(minutes=name_list['delta_time'] * lead)
    path = (f"{OUTPUT}forecast_{tag}/{anchor:%Y%m%d_%H%M}/forecast_images/{t:%Y%m%d_%H%M%S}.nc")
    if not os.path.exists(path):
        return None
    import xarray as xr
    return xr.open_dataarray(path).data[0]


def observed_image(anchor, lead):
    t = anchor + pd.Timedelta(minutes=name_list['delta_time'] * lead)
    path = INPUT + t.strftime(base.PATTERN) + '.nc'
    return read_function(path) if os.path.exists(path) else None


def run():
    # resume: only the frames not tracked yet (e.g. days added to DAYS_END) are processed
    pyfortracc.track(dict(name_list), read_function, parallel=True, resume=os.path.isdir(OUTPUT + 'track/'))
    from pyfortracc.forecast.flow_model import train_model
    for tag, forecast_name_list in FORECASTS.items():
        print(f'\n==== {LABELS[tag]} ====')
        if tag == 'flow_weights':
            forecast_name_list['rnn_weights'] = train_model(forecast_name_list, read_function)
        # pyfortracc.forecast writes to output_path/forecast/<anchor>/: the forecasts of each one are moved to
        # forecast_<tag>/, and the trained models stay in output_path/forecast/models/
        shutil.rmtree(OUTPUT + f'forecast_{tag}/', ignore_errors=True)
        os.makedirs(OUTPUT + f'forecast_{tag}/')
        for anchor in ANCHORS:
            shutil.rmtree(OUTPUT + f'forecast/{anchor:%Y%m%d_%H%M}/', ignore_errors=True)
            forecast_name_list['forecast_time'] = anchor.strftime('%Y-%m-%d %H:%M:%S')
            pyfortracc.forecast(forecast_name_list, read_function)
            shutil.move(OUTPUT + f'forecast/{anchor:%Y%m%d_%H%M}/', OUTPUT + f'forecast_{tag}/')


def evaluate():
    rows = []
    for tag in FORECASTS:
        for anchor in ANCHORS:
            for lead in range(1, name_list['lead_time'] + 1):
                fc, obs = forecast_image(tag, anchor, lead), observed_image(anchor, lead)
                if fc is None or obs is None:
                    continue
                for thr in name_list['thresholds']:
                    rows.append(dict(config=tag, anchor=anchor, lead=lead * name_list['delta_time'],
                                     threshold=thr, **scores(fc, obs, thr)))
    cases = pd.DataFrame(rows)
    cases['CSI'] = cases['hits'] / (cases['hits'] + cases['misses'] + cases['false']).clip(lower=1)
    df = cases.groupby(['config', 'threshold', 'lead'])[['hits', 'misses', 'false', 'f_area', 'o_area']] \
        .sum().reset_index()
    df['POD'] = df['hits'] / (df['hits'] + df['misses'])
    df['FAR'] = df['false'] / (df['hits'] + df['false'])
    df['CSI'] = df['hits'] / (df['hits'] + df['misses'] + df['false'])
    df['area_bias'] = df['f_area'] / df['o_area']
    df.to_csv(OUTPUT + 'forecast_flow_scores.csv', index=False)
    return df, cases


def plot_scores(df):
    thresholds = name_list['thresholds']
    fig, axes = plt.subplots(len(thresholds), 4, figsize=(16, 3.4 * len(thresholds)), sharex=True)
    for i, thr in enumerate(thresholds):
        for j, score in enumerate(['CSI', 'POD', 'FAR', 'area_bias']):
            ax = axes[i, j]
            for tag in FORECASTS:
                d = df[(df['config'] == tag) & (df['threshold'] == thr)]
                ax.plot(d['lead'], d[score], marker='o', ms=3, color=COLORS[tag], label=LABELS[tag])
            if score == 'area_bias':
                ax.axhline(1, color='k', lw=0.8, ls='--')
            ax.set_title(f'{score} | BT <= {thr} K')
            ax.grid(alpha=0.3)
            if i == len(thresholds) - 1:
                ax.set_xlabel('Lead time (min)')
    axes[0, 0].legend(fontsize=7)
    fig.suptitle(f'GOES-19 CH13 forecast scores by mode, {len(ANCHORS)} anchors '
                 f'{ANCHORS[0]:%H:%M}-{ANCHORS[-1]:%H:%M} UTC {ANCHORS[0]:%Y-%m-%d}')
    fig.tight_layout()
    fig.savefig(OUTPUT + 'forecast_flow_scores.png', dpi=120)
    plt.close(fig)


def plot_comparison(anchor, leads=(1, 6, 18, 36), tags=('persistence', 'morph_trend', 'lstm', 'flow')):
    extent = [name_list['lon_min'], name_list['lon_max'], name_list['lat_min'], name_list['lat_max']]
    fig, axes = plt.subplots(len(leads), 1 + len(tags), figsize=(4.4 * (1 + len(tags)), 3.8 * len(leads)),
                             squeeze=False)
    kw = dict(origin='lower', extent=extent, cmap='turbo_r', vmin=190, vmax=240)
    for i, lead in enumerate(leads):
        obs = observed_image(anchor, lead)
        if obs is None:
            continue
        t = anchor + pd.Timedelta(minutes=name_list['delta_time'] * lead)
        panels = [('Observed', np.where(obs <= 235, obs, np.nan))]
        panels += [(LABELS[tag], forecast_image(tag, anchor, lead)) for tag in tags]
        for j, (title, img) in enumerate(panels):
            ax = axes[i, j]
            ax.imshow(np.where(np.isfinite(obs), 1, np.nan), origin='lower', extent=extent, cmap='Greys',
                      vmin=0, vmax=4)
            if img is not None:
                im = ax.imshow(img, **kw)
            ax.contour(np.linspace(extent[0], extent[1], obs.shape[1]),
                       np.linspace(extent[2], extent[3], obs.shape[0]),
                       (obs <= 235).astype(float), levels=[0.5], colors='k', linewidths=0.6)
            if j > 0 and img is not None:
                s = scores(img, obs, 235)
                title += f"\nCSI(235 K) = {s['hits'] / max(s['hits'] + s['misses'] + s['false'], 1):.3f}"
            ax.set_title(f'{title}\n{t:%H:%M} UTC (+{lead * name_list["delta_time"]} min)', fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.colorbar(im, ax=axes, shrink=0.6, label='Brightness temperature (K)')
    fig.suptitle(f'GOES-19 CH13 forecast from {anchor:%Y-%m-%d %H:%M} UTC (black contour: observed 235 K)')
    fig.savefig(OUTPUT + f"forecast_flow_comparison_{anchor:%Y%m%d_%H%M}.png", dpi=100, bbox_inches='tight')
    plt.close(fig)


def summary(df, cases):
    print('\nCSI at the first lead time and every hour (all anchors), BT <= 235 K:')
    csi = df[df['threshold'] == 235].pivot(index='lead', columns='config', values='CSI')[list(FORECASTS)]
    print(csi[(csi.index == name_list['delta_time']) | (csi.index % 60 == 0)].round(3).to_string())
    print('\nMean CSI over the lead times, per threshold:')
    print(df.pivot_table(index='threshold', columns='config', values='CSI')[list(FORECASTS)].round(3).to_string())
    print('\nCases (anchor x lead x threshold) where each mode has a higher CSI than persistence / morph_trend:')
    ref = cases.set_index(['config', 'anchor', 'lead', 'threshold'])['CSI']
    for tag in FORECASTS:
        if tag in ('persistence', 'morph_trend'):
            continue
        csi = ref.loc[tag]
        wins = [int((csi > ref.loc[r]).sum()) for r in ('persistence', 'morph_trend')]
        print(f'  {LABELS[tag]:32s} {wins[0]:3d} / {len(csi)} vs persistence, '
              f'{wins[1]:3d} / {len(csi)} vs morph_trend')


if __name__ == '__main__':
    download()
    if 'download' in sys.argv[1:]:
        sys.exit()
    if 'plots' not in sys.argv[1:]:
        run()
    df, cases = evaluate()
    plot_scores(df)
    for anchor in ANCHORS:
        plot_comparison(anchor)
    summary(df, cases)
