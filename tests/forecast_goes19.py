"""
Persistence forecast of GOES-19 infrared (ABI channel 13, brightness temperature) convective systems,
with and without the trends of the systems (name_list['morph_trend']: dilation/erosion and intensity trend).

The images are downloaded and cropped/reprojected to a regular lat/lon grid with goesgcp
(https://github.com/helvecioneto/goesgcp). The script tracks the systems, forecasts from several
anchor times with morph_trend off and on and writes, in output_goes19/:
    - forecast_comparison_<anchor>.png: observed | persistence | persistence + morph_trend
    - forecast_zoom_<anchor>_<growing|decaying>.png: the same, zoomed on the system with the strongest
      growth / decay, plus the contours of the three fields overlaid
    - forecast_scores.png and forecast_scores.csv: POD, FAR, CSI and area bias per lead time

Run from the tests directory: python forecast_goes19.py
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
import xarray as xr

sys.path.append('../')
import pyfortracc
from pyfortracc.forecast.morphology import system_trends

# GOES-19 event: deep convection over Mato Grosso do Sul / Mato Grosso, Brazil
SATELLITE, PRODUCT, CHANNEL = 'goes-19', 'ABI-L2-CMIPF', 13
START, END = '2025-11-05 16:00:00', '2025-11-05 22:00:00'
BOX = dict(lat_min=-24, lat_max=-12, lon_min=-60, lon_max=-46)
RESOLUTION = 0.04
INPUT = 'input_goes19/'
OUTPUT = 'output_goes19/'
PATTERN = 'goes19_ch13_%Y%m%d_%H%M'

# Forecast experiment
ANCHORS = pd.date_range('2025-11-05 18:00', '2025-11-05 20:00', freq='30min')
CONFIGS = {'persistence': dict(morph_trend=False),
           'morph_trend': dict(morph_trend=True)}
LABELS = {'persistence': 'Persistence',
          'morph_trend': 'Persistence + morph_trend'}
COLORS = {'persistence': 'tab:blue', 'morph_trend': 'tab:red'}
TAGS = tuple(CONFIGS)


def download_goes19():
    """Download and crop the GOES-19 images with goesgcp (skipped when they are already there)."""
    expected = len(pd.date_range(START, END, freq='10min'))
    if len(glob.glob(INPUT + '*.nc')) >= expected:
        return
    # goesgcp reprojects with the .rio accessor but does not import rioxarray,
    # so it is imported before calling its main. The PROJ database of a conda
    # installation (PROJ_DATA) may not match the one bundled with the rasterio
    # wheel, so it is not passed to the download.
    code = 'import sys, rioxarray\nfrom goesgcp.main import main\nsys.argv = sys.argv[1:]\nmain()'
    args = ['goesgcp', '--satellite', SATELLITE, '--product', PRODUCT, '--channel', str(CHANNEL),
            '--var_name', 'CMI', '--start', START, '--end', END, '--freq', '10 min',
            '--resolution', str(RESOLUTION), '--output', INPUT, '--file_pattern', PATTERN,
            '--parallel', 'False']
    for key, value in BOX.items():
        args += [f'--{key}', str(value)]
    env = {k: v for k, v in os.environ.items() if k not in ('PROJ_DATA', 'PROJ_LIB')}
    subprocess.run([sys.executable, '-c', code] + args, env=env, check=True)


def read_function(path):
    """Brightness temperature (K) with row 0 at the southernmost latitude, as pyfortracc expects."""
    with xr.open_dataset(path) as ds:
        data = ds['CMI'].sortby('lat').values.astype(float)
    return data


def grid_bounds(path):
    """Outer edges of the grid from the pixel-centre coordinates of a goesgcp file."""
    with xr.open_dataset(path) as ds:
        lat, lon = np.sort(ds['lat'].values), np.sort(ds['lon'].values)
    dy, dx = np.diff(lat).mean(), np.diff(lon).mean()
    return dict(lat_min=lat[0] - dy / 2, lat_max=lat[-1] + dy / 2,
                lon_min=lon[0] - dx / 2, lon_max=lon[-1] + dx / 2)


name_list = {}
name_list['input_path'] = INPUT
name_list['output_path'] = OUTPUT
name_list['timestamp_pattern'] = PATTERN + '.nc'
name_list['thresholds'] = [235, 220, 210]        # brightness temperature (K): cloud shield, convection, deep cores
name_list['min_cluster_size'] = [30, 15, 5]      # pixels of ~4.4 km
name_list['operator'] = '<='
name_list['delta_time'] = 10                     # minutes
name_list['min_overlap'] = 10
name_list['spl_correction'] = True
name_list['mrg_correction'] = True
name_list['inc_correction'] = True
name_list['opt_correction'] = True
name_list['new_correction'] = True               # NEW clusters (also in the forecast frames) get the neighbours' vector
name_list['edges'] = False
name_list['observation_window'] = 3              # 30 minutes of history for the vectors and the trends
name_list['lead_time'] = 6                       # 1 hour of forecast


def forecast_image(tag, anchor, lead):
    t = anchor + pd.Timedelta(minutes=name_list['delta_time'] * lead)
    path = (f"{OUTPUT}forecast_{tag}/{anchor.strftime('%Y%m%d_%H%M')}/forecast_images/"
            f"{t.strftime('%Y%m%d_%H%M%S')}.nc")
    if not os.path.exists(path):
        return None
    return xr.open_dataarray(path).data[0]


def observed_image(anchor, lead):
    t = anchor + pd.Timedelta(minutes=name_list['delta_time'] * lead)
    path = INPUT + t.strftime(PATTERN) + '.nc'
    return read_function(path) if os.path.exists(path) else None


def scores(fc, obs, thr):
    """Contingency scores of the area colder than thr (fc NaN = no system forecast)."""
    f = np.nan_to_num(fc, nan=np.inf) <= thr
    o = obs <= thr
    hits, misses, false = np.sum(f & o), np.sum(~f & o), np.sum(f & ~o)
    return dict(hits=hits, misses=misses, false=false, f_area=f.sum(), o_area=o.sum())


def evaluate():
    rows = []
    for tag in CONFIGS:
        for anchor in ANCHORS:
            for lead in range(1, name_list['lead_time'] + 1):
                fc, obs = forecast_image(tag, anchor, lead), observed_image(anchor, lead)
                if fc is None or obs is None:
                    continue
                for thr in name_list['thresholds']:
                    rows.append(dict(config=tag, anchor=anchor, lead=lead * name_list['delta_time'],
                                     threshold=thr, **scores(fc, obs, thr)))
    df = pd.DataFrame(rows).groupby(['config', 'threshold', 'lead'])[
        ['hits', 'misses', 'false', 'f_area', 'o_area']].sum().reset_index()
    df['POD'] = df['hits'] / (df['hits'] + df['misses'])
    df['FAR'] = df['false'] / (df['hits'] + df['false'])
    df['CSI'] = df['hits'] / (df['hits'] + df['misses'] + df['false'])
    df['area_bias'] = df['f_area'] / df['o_area']
    df.to_csv(OUTPUT + 'forecast_scores.csv', index=False)
    return df


def plot_scores(df):
    fig, axes = plt.subplots(len(name_list['thresholds']), 4, figsize=(16, 3.4 * len(name_list['thresholds'])),
                             sharex=True)
    for i, thr in enumerate(name_list['thresholds']):
        for j, score in enumerate(['CSI', 'POD', 'FAR', 'area_bias']):
            ax = axes[i, j]
            for tag in CONFIGS:
                d = df[(df['config'] == tag) & (df['threshold'] == thr)]
                ax.plot(d['lead'], d[score], marker='o', label=LABELS[tag])
            if score == 'area_bias':
                ax.axhline(1, color='k', lw=0.8, ls='--')
            ax.set_title(f'{score} | BT <= {thr} K')
            ax.grid(alpha=0.3)
            if i == len(name_list['thresholds']) - 1:
                ax.set_xlabel('Lead time (min)')
    axes[0, 0].legend(fontsize=8)
    fig.suptitle(f'GOES-19 CH13 forecast scores, anchors {ANCHORS[0]:%H:%M}-{ANCHORS[-1]:%H:%M} UTC '
                 f'{ANCHORS[0]:%Y-%m-%d}')
    fig.tight_layout()
    fig.savefig(OUTPUT + 'forecast_scores.png', dpi=120)
    plt.close(fig)


def plot_comparison(anchor, leads=(1, 3, 6), tags=TAGS):
    """Rows: lead times. Columns: observed, then each configuration, with the observed 235 K contour."""
    extent = [name_list['lon_min'], name_list['lon_max'], name_list['lat_min'], name_list['lat_max']]
    fig, axes = plt.subplots(len(leads), 1 + len(tags), figsize=(5.2 * (1 + len(tags)), 4.3 * len(leads)),
                             squeeze=False)
    kw = dict(origin='lower', extent=extent, cmap='turbo_r', vmin=190, vmax=240)
    for i, lead in enumerate(leads):
        obs = observed_image(anchor, lead)
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
                       (obs <= 235).astype(float), levels=[0.5], colors='k', linewidths=0.7)
            if j > 0:
                s = scores(img, obs, 235)
                csi = s['hits'] / max(s['hits'] + s['misses'] + s['false'], 1)
                title += f"\nCSI(235 K) = {csi:.2f} | area bias = {s['f_area'] / max(s['o_area'], 1):.2f}"
            ax.set_title(f'{title}\n{t:%Y-%m-%d %H:%M} UTC (+{lead * name_list["delta_time"]} min)', fontsize=9)
    fig.colorbar(im, ax=axes, shrink=0.6, label='Brightness temperature (K)')
    fig.suptitle(f'GOES-19 CH13 forecast from {anchor:%Y-%m-%d %H:%M} UTC '
                 f'(black contour: observed 235 K)')
    out = OUTPUT + f"forecast_comparison_{anchor.strftime('%Y%m%d_%H%M')}.png"
    fig.savefig(out, dpi=110, bbox_inches='tight')
    plt.close(fig)
    return out


def trend_systems(anchor, min_size=80):
    """The systems (first threshold) at the anchor with the strongest growth and decay over the observation window,
    with their area rate, mean vector (pixels per step) and pixels, as seen by the persistence forecast."""
    files = sorted(glob.glob(OUTPUT + 'track/trackingtable/*.parquet'))
    files = [f for f in files if os.path.basename(f) <= anchor.strftime('%Y%m%d_%H%M') + '.parquet']
    df = pd.concat([pd.read_parquet(f) for f in files[-name_list['observation_window']:]], ignore_index=True)
    df['uid'] = df['iuid'].where(df['iuid'].notna(), df['uid'])
    trends = system_trends(df, name_list)
    trends['area_rate'] = np.exp(trends['log_rate'])
    level0 = df[df['threshold_level'] == 0]
    shape = observed_image(anchor, 0).shape
    vectors = level0.groupby('uid').agg(dx=('u_', 'mean'), dy=('v_', 'mean'))
    vectors['dx'] /= (name_list['lon_max'] - name_list['lon_min']) / shape[1]
    vectors['dy'] /= (name_list['lat_max'] - name_list['lat_min']) / shape[0]
    last = level0[(level0['timestamp'] == level0['timestamp'].max()) & (level0['size'] >= min_size) &
                  level0['u_'].notna()]
    last = last.merge(trends[trends['threshold_level'] == 0], on=['threshold_level', 'uid'])
    last = last.join(vectors, on='uid')
    picks = [('growing', last.loc[last['area_rate'].idxmax()]), ('decaying', last.loc[last['area_rate'].idxmin()])]
    return [(kind, row) for kind, row in picks if row['area_rate'] != 1]


def plot_zoom(anchor, leads=(1, 3, 6), tags=TAGS, pad=12):
    """
    Zoom on the system with the strongest growth and on the one with the strongest decay at the anchor. The window
    follows the system along the whole forecast (its anchor pixels moved by its mean vector up to the last lead).
    Last column: contours of the observed (black) and of each configuration (COLORS) at 235 K (solid) and 210 K
    (dashed), where the dilation/erosion shows as the gap between the persistence (blue) and the other lines.
    """
    shape = observed_image(anchor, 0).shape
    x_res = (name_list['lon_max'] - name_list['lon_min']) / shape[1]
    y_res = (name_list['lat_max'] - name_list['lat_min']) / shape[0]
    outs = []
    for kind, sys_row in trend_systems(anchor):
        xs, ys = np.asarray(sys_row['array_x']), np.asarray(sys_row['array_y'])
        steps = np.arange(max(leads) + 1)
        all_x = (xs[:, None] + np.round(sys_row['dx'] * steps)[None, :]).ravel()
        all_y = (ys[:, None] + np.round(sys_row['dy'] * steps)[None, :]).ravel()
        x0, x1 = int(max(all_x.min() - pad, 0)), int(min(all_x.max() + pad + 1, shape[1]))
        y0, y1 = int(max(all_y.min() - pad, 0)), int(min(all_y.max() + pad + 1, shape[0]))
        extent = [name_list['lon_min'] + x0 * x_res, name_list['lon_min'] + x1 * x_res,
                  name_list['lat_min'] + y0 * y_res, name_list['lat_min'] + y1 * y_res]
        lon = name_list['lon_min'] + (np.arange(x0, x1) + 0.5) * x_res
        lat = name_list['lat_min'] + (np.arange(y0, y1) + 0.5) * y_res
        ncol = 2 + len(tags)
        fig, axes = plt.subplots(len(leads), ncol, figsize=(3.6 * ncol, 3.4 * len(leads)), squeeze=False)
        kw = dict(origin='lower', extent=extent, cmap='turbo_r', vmin=190, vmax=240, interpolation='nearest')
        for i, lead in enumerate(leads):
            t = anchor + pd.Timedelta(minutes=name_list['delta_time'] * lead)
            obs = observed_image(anchor, lead)[y0:y1, x0:x1]
            fcs = {tag: forecast_image(tag, anchor, lead)[y0:y1, x0:x1] for tag in tags}
            panels = [('Observed', np.where(obs <= 235, obs, np.nan))] + [(LABELS[tag], fcs[tag]) for tag in tags]
            for j, (title, img) in enumerate(panels):
                ax = axes[i, j]
                ax.set_facecolor('0.85')
                im = ax.imshow(img, **kw)
                if j > 0:
                    n235, o235 = np.count_nonzero(np.nan_to_num(img, nan=999) <= 235), np.count_nonzero(obs <= 235)
                    title += f'\n235 K area: {n235} px (observed {o235})'
                ax.set_title(f'{title}\n+{lead * name_list["delta_time"]} min ({t:%H:%M} UTC)', fontsize=8)
            ax = axes[i, -1]
            ax.imshow(obs, origin='lower', extent=extent, cmap='Greys', vmin=190, vmax=300, interpolation='nearest')
            ax.contour(lon, lat, obs, levels=[210, 235], colors='k', linestyles=['--', '-'], linewidths=1.2)
            for tag in tags:
                ax.contour(lon, lat, np.nan_to_num(fcs[tag], nan=999), levels=[210, 235], colors=COLORS[tag],
                           linestyles=['--', '-'], linewidths=1.2)
            ax.set_title('Contours: 235 K (solid), 210 K (dashed)', fontsize=8)
        handles = [plt.Line2D([], [], color='k', label='Observed')]
        handles += [plt.Line2D([], [], color=COLORS[tag], label=LABELS[tag]) for tag in tags]
        fig.legend(handles=handles, loc='lower center', ncol=len(handles), fontsize=9, bbox_to_anchor=(0.5, -0.02))
        fig.colorbar(im, ax=axes[:, :-1], shrink=0.6, label='Brightness temperature (K)')
        fig.suptitle(f'{kind.capitalize()} system uid {int(sys_row["uid"])} at {anchor:%Y-%m-%d %H:%M} UTC: '
                     f'{int(sys_row["size"])} px, area rate {sys_row["area_rate"]:.2f} per '
                     f'{name_list["delta_time"]} min', fontsize=11)
        out = OUTPUT + f"forecast_zoom_{anchor.strftime('%Y%m%d_%H%M')}_{kind}.png"
        fig.savefig(out, dpi=120, bbox_inches='tight')
        plt.close(fig)
        outs.append(out)
    return outs


if __name__ == '__main__':
    # python forecast_goes19.py plots -> only redraw the figures from an existing run
    only_plots = 'plots' in sys.argv[1:]
    download_goes19()
    name_list.update(grid_bounds(sorted(glob.glob(INPUT + '*.nc'))[0]))
    if only_plots:
        for anchor in ANCHORS:
            plot_comparison(anchor)
            plot_zoom(anchor)
        sys.exit()

    pyfortracc.track(name_list, read_function, parallel=True)

    # The same tracking is forecast with each configuration; pyfortracc.forecast
    # always writes to output_path/forecast/, which is renamed per configuration
    for tag, config in CONFIGS.items():
        shutil.rmtree(OUTPUT + 'forecast/', ignore_errors=True)
        shutil.rmtree(OUTPUT + f'forecast_{tag}/', ignore_errors=True)
        for anchor in ANCHORS:
            pyfortracc.forecast(dict(name_list, forecast_time=anchor.strftime('%Y-%m-%d %H:%M:%S'), **config),
                                read_function)
        os.rename(OUTPUT + 'forecast/', OUTPUT + f'forecast_{tag}/')

    df = evaluate()
    plot_scores(df)
    for anchor in ANCHORS:
        plot_comparison(anchor)
        plot_zoom(anchor)
    summary = df[df['threshold'] == 235].pivot(index='lead', columns='config', values=['CSI', 'area_bias'])
    print('\nScores for BT <= 235 K (all anchors):\n', summary.round(3).to_string())
