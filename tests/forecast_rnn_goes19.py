"""
Comparison of the forecast modes on one day of GOES-19 infrared (ABI channel 13, brightness temperature)
convective systems over Mato Grosso do Sul / Mato Grosso, Brazil (2025-11-05): persistence, persistence +
morph_trend and the recurrent modes (forecast_mode 'lstm' and 'gru').

The day is downloaded with goesgcp (https://github.com/helvecioneto/goesgcp) and tracked with the name_list
below (the settings of forecast_goes19.py). The forecasts start every hour of ANCHORS, 1 hour ahead. Two
ways of using the recurrent models are compared:
    - rolling: the model is retrained at every anchor on the whole tracking up to the anchor (the default,
      name_list['rnn_train_period'] = None);
    - pretrained: the model is trained once on the frames of TRAIN_PERIOD (the morning, 00:00 to 12:00):
      the LSTM by pyfortracc.forecast with name_list['rnn_train_period'] (trained at the first anchor, then
      reused from output_path/forecast/models/), the GRU, tuned with optuna (name_list['rnn_arch'] =
      'optuna'), by pyfortracc.forecast.rnn_model.train_model and then only used for inference at the
      anchors (name_list['rnn_weights']).
No observation after an anchor is used to forecast from it. Writes, in output_goes19_rnn/:
    - forecast_<tag>/: the forecasts of each one; forecast/models/: the trained models
    - forecast_rnn_scores.csv and forecast_rnn_scores.png: POD, FAR, CSI and area bias per lead time
    - forecast_rnn_comparison_<anchor>.png: observed and each forecast at +10, +30 and +60 min

Needs PyTorch, optuna and goesgcp (pip install torch optuna goesgcp). Run from the tests directory:
python forecast_rnn_goes19.py (python forecast_rnn_goes19.py plots only redraws the figures).
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

DAY_START, DAY_END = '2025-11-05 00:00:00', '2025-11-05 23:50:00'   # day downloaded and tracked
TRAIN_END = pd.Timestamp('2025-11-05 12:00')                         # end of the training of the pretrained models
TRAIN_PERIOD = [DAY_START, str(TRAIN_END)]                           # their rnn_train_period: the morning
ANCHORS = pd.date_range('2025-11-05 12:00', '2025-11-05 22:00', freq='1h')   # forecast_time of each forecast
INPUT = 'input_goes19_rnn/'
OUTPUT = 'output_goes19_rnn/'

# Set the parameters
name_list = {}
name_list['input_path'] = INPUT # path to the input data
name_list['output_path'] = OUTPUT # path to the output data (tracking, forecasts and trained models)
name_list['timestamp_pattern'] = base.PATTERN + '.nc' # timestamp file pattern: goes19_ch13_%Y%m%d_%H%M.nc
name_list['thresholds'] = [235, 220, 210] # brightness temperature (K): cloud shield, convection, deep cores
name_list['min_cluster_size'] = [30, 15, 5] # in number of pixels (~4.4 km) per cluster
name_list['operator'] = '<=' # colder than the thresholds
name_list['delta_time'] = 10 # in minutes
name_list['min_overlap'] = 10 # Minimum overlap between clusters in percentage

# Not mandatory parameters, if not set, the algorithm will use the default values
name_list['spl_correction'] = True # Set to True to apply the Split correction
name_list['mrg_correction'] = True # Set to True to apply the Merge correction
name_list['inc_correction'] = True # Set to True to apply the Inner Cores correction
name_list['opt_correction'] = True # Set to True to apply the Optical Flow correction
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
name_list['lead_time'] = 6 # Amount of time steps to forecast (1 hour)
name_list['forecast_mode'] = 'persistence' # 'persistence', 'lstm' or 'gru' (each forecast below sets its own)
name_list['morph_trend'] = False # Persistence only: dilate/erode the systems by their area trend

# Recurrent forecast parameters (forecast_mode 'lstm' or 'gru'), here with their default values
name_list['rnn_weights'] = None # None: train the model (saved in output_path/forecast/models/);
                                # a path to a .pt file: use that trained model, for inference only
name_list['rnn_train_period'] = None # None: train on the whole tracking up to forecast_time;
                                     # [start, end]: train on the frames of that period only
name_list['rnn_aux'] = [] # extra columns of the tracking table used by the model, e.g. ['land_use']
name_list['rnn_arch'] = None # None: default architecture; a dict to change it, e.g. {'hidden': 64,
                             # 'layers': 2, 'seq_len': 6 (time steps of history), 'device': 'cpu'};
                             # 'optuna': search the architecture with optuna

# The test compares six forecasts. Each one is run by pyfortracc.forecast with its own name_list: a copy of
# the name_list above in which only the forecast parameters written below change.
FORECASTS = {}

# 1. Persistence: each system is moved by its mean vector over the observation_window, keeping its shape
name_list_persistence = dict(name_list)
name_list_persistence['forecast_mode'] = 'persistence'
FORECASTS['persistence'] = name_list_persistence

# 2. Persistence + morph_trend: the systems also grow or decay by their trends over the observation_window
name_list_morph_trend = dict(name_list)
name_list_morph_trend['forecast_mode'] = 'persistence'
name_list_morph_trend['morph_trend'] = True
FORECASTS['morph_trend'] = name_list_morph_trend

# 3. LSTM retrained at every anchor on the whole tracking up to the anchor (rnn_train_period None)
name_list_lstm = dict(name_list)
name_list_lstm['forecast_mode'] = 'lstm'
FORECASTS['lstm'] = name_list_lstm

# 4. GRU retrained at every anchor on the whole tracking up to the anchor
name_list_gru = dict(name_list)
name_list_gru['forecast_mode'] = 'gru'
FORECASTS['gru'] = name_list_gru

# 5. LSTM trained once on the morning: pyfortracc.forecast trains it at the first anchor and saves it in
#    output_path/forecast/models/; the next anchors find it there and reuse it
name_list_lstm_morning = dict(name_list)
name_list_lstm_morning['forecast_mode'] = 'lstm'
name_list_lstm_morning['rnn_train_period'] = TRAIN_PERIOD
FORECASTS['lstm_pretrained'] = name_list_lstm_morning

# 6. GRU with its architecture searched by optuna, trained once on the morning with
#    pyfortracc.forecast.rnn_model.train_model before the forecasts (in run()); the forecasts then only use
#    its weights (inference), given in rnn_weights
name_list_gru_optuna = dict(name_list)
name_list_gru_optuna['forecast_mode'] = 'gru'
name_list_gru_optuna['rnn_arch'] = 'optuna'
name_list_gru_optuna['rnn_train_period'] = TRAIN_PERIOD
name_list_gru_optuna['rnn_weights'] = None # set in run() to the path returned by train_model
FORECASTS['gru_optuna_pretrained'] = name_list_gru_optuna

LABELS = {'persistence': 'Persistence', 'morph_trend': 'Persistence + morph_trend', 'lstm': 'LSTM (rolling)',
          'gru': 'GRU (rolling)', 'lstm_pretrained': f'LSTM (trained 00:00-{TRAIN_END:%H:%M})',
          'gru_optuna_pretrained': f'GRU optuna (trained 00:00-{TRAIN_END:%H:%M})'}
COLORS = {'persistence': 'tab:blue', 'morph_trend': 'tab:red', 'lstm': 'tab:green', 'gru': 'tab:purple',
          'lstm_pretrained': 'tab:olive', 'gru_optuna_pretrained': 'tab:orange'}


def download():
    """Download and crop the GOES-19 images of the day with goesgcp (skipped when they are already there)."""
    expected = len(pd.date_range(DAY_START, DAY_END, freq='10min'))
    if len(glob.glob(INPUT + '*.nc')) >= expected:
        return
    # See forecast_goes19.download_goes19 for the rioxarray import and the PROJ variables
    code = 'import sys, rioxarray\nfrom goesgcp.main import main\nsys.argv = sys.argv[1:]\nmain()'
    args = ['goesgcp', '--satellite', base.SATELLITE, '--product', base.PRODUCT, '--channel', str(base.CHANNEL),
            '--var_name', 'CMI', '--start', DAY_START, '--end', DAY_END, '--freq', '10 min',
            '--resolution', str(base.RESOLUTION), '--output', INPUT, '--file_pattern', base.PATTERN,
            '--parallel', 'True', '--processes', '8']
    for key, value in base.BOX.items():
        args += [f'--{key}', str(value)]
    env = {k: v for k, v in os.environ.items() if k not in ('PROJ_DATA', 'PROJ_LIB')}
    subprocess.run([sys.executable, '-c', code] + args, env=env, check=True)


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
    if not os.path.isdir(OUTPUT + 'track/trackingtable/'):
        pyfortracc.track(name_list, read_function, parallel=True)
    from pyfortracc.forecast.rnn_model import train_model
    for tag, forecast_name_list in FORECASTS.items():
        print(f'\n==== {LABELS[tag]} ====')
        if tag == 'gru_optuna_pretrained':
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
    df.to_csv(OUTPUT + 'forecast_rnn_scores.csv', index=False)
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
    fig.savefig(OUTPUT + 'forecast_rnn_scores.png', dpi=120)
    plt.close(fig)


def plot_comparison(anchor, leads=(1, 3, 6), tags=('persistence', 'morph_trend', 'lstm', 'gru')):
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
            im = ax.imshow(img, **kw)
            ax.contour(np.linspace(extent[0], extent[1], obs.shape[1]),
                       np.linspace(extent[2], extent[3], obs.shape[0]),
                       (obs <= 235).astype(float), levels=[0.5], colors='k', linewidths=0.6)
            if j > 0:
                s = scores(img, obs, 235)
                title += f"\nCSI(235 K) = {s['hits'] / max(s['hits'] + s['misses'] + s['false'], 1):.3f}"
            ax.set_title(f'{title}\n{t:%H:%M} UTC (+{lead * name_list["delta_time"]} min)', fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.colorbar(im, ax=axes, shrink=0.6, label='Brightness temperature (K)')
    fig.suptitle(f'GOES-19 CH13 forecast from {anchor:%Y-%m-%d %H:%M} UTC (black contour: observed 235 K)')
    fig.savefig(OUTPUT + f"forecast_rnn_comparison_{anchor:%Y%m%d_%H%M}.png", dpi=100, bbox_inches='tight')
    plt.close(fig)


def summary(df, cases):
    print('\nCSI per lead time (all anchors), BT <= 235 K:')
    print(df[df['threshold'] == 235].pivot(index='lead', columns='config', values='CSI')[list(FORECASTS)]
          .round(3).to_string())
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
    if 'plots' not in sys.argv[1:]:
        run()
    df, cases = evaluate()
    plot_scores(df)
    for anchor in ANCHORS:
        plot_comparison(anchor)
    summary(df, cases)
