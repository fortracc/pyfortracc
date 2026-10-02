
import gdown, zipfile, os, shutil
import sys
import os

import pandas as pd
import glob
import zipfile
sys.path.append('../')
import pyfortracc
# Set the read function
import gzip
import netCDF4
import numpy as np
import xarray as xr

def read_function(path):
    variable = "DBZc"
    z_level = 0 # Elevation level 2.5 km
    with gzip.open(path) as gz:
        with netCDF4.Dataset("dummy", mode="r", memory=gz.read()) as nc:
            data = nc.variables[variable][:].data[0,z_level, :, :]
            data[data == -9999] = np.nan
    gz.close()
    return data
# Set the parameters
name_list = {}
name_list['input_path'] = 'input/' # path to the input data
name_list['output_path'] = 'output/' # path to the output data
name_list['timestamp_pattern'] = 'sbmn_cappi_%Y%m%d_%H%M.nc.gz' # timestamp file pattern
name_list['thresholds'] = [20, 30, 35] # in dbz
name_list['min_cluster_size'] = [3,3,3] # in number of points per cluster
name_list['operator'] = '>=' # '>= *   **<=' or '=='
name_list['delta_time'] = 12 # in minutes
name_list['min_overlap'] = 5 # Minimum overlap between clusters in percentage

# Not mandatory parameters, if not set, the algorithm will use the default values
name_list['track_start'] = '2014-08-16 11:00:00' # Start time of the tracking in UTC
name_list['track_end'] = '2014-08-16 14:00:00' # End time of the tracking in UTC

name_list['spl_correction'] = True # Set to True to apply the Split correction
name_list['mrg_correction'] = True # Set to True to apply the Merge correction
name_list['inc_correction'] = True # Set to True to apply the Inner Cores correction
name_list['opt_correction'] = True # Set to True to apply the Optical Flow correction
name_list['elp_correction'] = True # Set to True to apply the Ellipse correction
name_list['new_correction'] = True # Set to True to apply the NEW correction
name_list['validation'] = True # Set to True to apply the validation of corrections
name_list['validation_scores'] = True  # Set to True to get the scores of the validation
#TODO

# Optional parameters, if not set, the algorithm will not use geospatial information
name_list['lon_min'] = -62.1475 # Min longitude of data in degrees
name_list['lon_max'] = -57.8461 # Max longitude of data in degrees
name_list['lat_min'] = -5.3048 # Min latitude of data in degrees
name_list['lat_max'] = -0.9912 # Max latitude of data in degrees

name_list['forecast_time'] = '2014-08-16 14:00:00' # Overwritten by the rolling-origin loop below
name_list['observation_window'] = 2 # Number of previous images
name_list['lead_time'] = 3 # Amount of time to forecast

name_list['edges'] = False # If True, the edges of the clusters will be considered in the tracking


def read_table(files):
    """Read and concatenate tracking table parquet files."""
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def check_uv_axes(name_list):
    """Check on the observed tracking that u_ moves the clusters along the
    columns (array_x) and v_ along the rows (array_y). For each cluster
    followed between two consecutive frames, the displacement of its pixel
    centroid is compared with u_/x_res and v_/y_res (correct mapping) and
    with the swapped mapping. The correct mapping must fit much better."""
    files = sorted(glob.glob(name_list['output_path'] + 'track/trackingtable/*.parquet'))
    df = read_table(files)
    y_dim, x_dim = read_function(sorted(glob.glob(name_list['input_path'] + '*'))[0]).shape
    x_res = (name_list['lon_max'] - name_list['lon_min']) / x_dim
    y_res = (name_list['lat_max'] - name_list['lat_min']) / y_dim
    df = df.dropna(subset=['uid', 'u_', 'v_'])
    df['cx'] = df['array_x'].apply(np.mean)
    df['cy'] = df['array_y'].apply(np.mean)
    df = df.sort_values(['threshold_level', 'uid', 'timestamp'])
    grp = df.groupby(['threshold_level', 'uid'])
    # Displacement of the pixel centroid between consecutive frames
    step = grp['timestamp'].diff() == pd.Timedelta(minutes=name_list['delta_time'])
    dx = grp['cx'].diff()[step]
    dy = grp['cy'].diff()[step]
    u_pix = df.loc[step, 'u_'] / x_res
    v_pix = df.loc[step, 'v_'] / y_res
    err_ok = np.median(np.hypot(dx - u_pix, dy - v_pix))
    err_swap = np.median(np.hypot(dx - v_pix, dy - u_pix))
    print(f"[check_uv_axes] {step.sum()} displacements | median error (pixels): "
          f"u_->x/v_->y = {err_ok:.3f}, u_->y/v_->x = {err_swap:.3f}")
    assert err_ok < err_swap, "u_/v_ do not follow array_x/array_y"


def expected_persistence(tracked_files, name_list, shape, swap=False):
    """Independent persistence oracle written with plain loops: each cluster
    at the anchor frame is moved by its mean vector over the observation
    window, u_ along the columns (x) and v_ along the rows (y). Pixels hit by
    more than one cluster receive the mean value. swap=True reproduces the
    old (wrong) mapping, used to show that the check discriminates."""
    h, w = shape
    x_res = (name_list['lon_max'] - name_list['lon_min']) / w
    y_res = (name_list['lat_max'] - name_list['lat_min']) / h
    df = read_table(tracked_files)
    # Multi-threshold clusters are followed by their iuid
    if len(name_list['thresholds']) > 1:
        df['key'] = df['iuid'].fillna(df['uid'])
    else:
        df['key'] = df['uid']
    anchor = df[df['timestamp'] == df['timestamp'].max()]
    sums, counts = np.zeros(shape), np.zeros(shape)
    for _, row in anchor.iterrows():
        if pd.isna(row['key']) or pd.isna(row['u_']) or pd.isna(row['v_']):
            continue
        hist = df[(df['threshold_level'] == row['threshold_level']) &
                  (df['key'] == row['key'])]
        dx = hist['u_'].mean() / x_res  # zonal -> columns
        dy = hist['v_'].mean() / y_res  # meridional -> rows
        if swap:
            dx, dy = hist['v_'].mean() / y_res, hist['u_'].mean() / x_res
        for y, x, val in zip(row['array_y'], row['array_x'], row['array_values']):
            yy = min(max(round(y + dy), 0), h - 1)
            xx = min(max(round(x + dx), 0), w - 1)
            sums[yy, xx] += val
            counts[yy, xx] += 1
    with np.errstate(invalid='ignore'):
        return sums / counts


def check_persistence(name_list, forecast_time):
    """Compare the first lead time forecast image written by
    pyfortracc.forecast with the oracle above."""
    anchor = pd.to_datetime(forecast_time)
    files = sorted(glob.glob(name_list['output_path'] + 'track/trackingtable/*.parquet'))
    files = [f for f in files
             if pd.to_datetime(os.path.basename(f)[:13], format='%Y%m%d_%H%M') <= anchor]
    files = files[-name_list['observation_window']:]
    lead1 = anchor + pd.Timedelta(minutes=name_list['delta_time'])
    image_file = (name_list['output_path'] + 'forecast/' + anchor.strftime('%Y%m%d_%H%M') +
                  '/forecast_images/' + lead1.strftime('%Y%m%d_%H%M%S.nc'))
    forecast_img = xr.open_dataarray(image_file).data[0]
    expected = expected_persistence(files, name_list, forecast_img.shape)
    swapped = expected_persistence(files, name_list, forecast_img.shape, swap=True)
    same_mask = np.array_equal(np.isnan(forecast_img), np.isnan(expected))
    same_vals = np.allclose(forecast_img, expected, equal_nan=True)
    diff_swap = np.sum(np.isnan(forecast_img) != np.isnan(swapped))
    print(f"[check_persistence] {forecast_time} | {np.sum(~np.isnan(expected))} forecast pixels | "
          f"mask ok: {same_mask} | values ok: {same_vals} | "
          f"pixels that would differ with u_/v_ swapped: {diff_swap}")
    assert same_mask and same_vals, f"persistence forecast mismatch at {forecast_time}"



if __name__ == '__main__':
    # Remove the existing input files
    shutil.rmtree('input', ignore_errors=True)

    # Download the input files
    url = 'https://drive.google.com/uc?id=1UVVsLCNnsmk7_wOzVrv4H7WHW0sz8spg'
    gdown.download(url, 'input.zip', quiet=False)
    with zipfile.ZipFile('input.zip', 'r') as zip_ref:
        for member in zip_ref.namelist():
            zip_ref.extract(member)
    os.remove('input.zip')

    pyfortracc.track(name_list, read_function, parallel=True)

    pyfortracc.spatial_conversions(name_list, boundary=True, trajectory=True, vector_field=True,
                                   cluster=True, vel_unit='m/s', driver='GeoJSON',
                                    start_time=name_list['track_start'],
                                    end_time=name_list['track_end'])

    # The tracked u_/v_ must follow the cluster pixels (u_ -> x, v_ -> y)
    check_uv_axes(name_list)

    for time in pd.date_range(start='2014-08-16 14:00:00', end='2014-08-16 17:00:00', freq='12min'):
        name_list['forecast_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        pyfortracc.forecast(name_list, read_function)
        # The first lead time must be the anchor clusters moved by their mean vector
        check_persistence(name_list, name_list['forecast_time'])
