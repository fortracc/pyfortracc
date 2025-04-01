import sys
import os
import xarray as xr
import pandas as pd
import glob
import requests
import zipfile
import io
sys.path.append('../')
import pyfortracc
# Set the read function
def read_function(path):
	data = xr.open_dataarray(path).data
	return data
# Set the parameters
name_list = {}
name_list['input_path'] = 'input/' # path to the input data
name_list['output_path'] = 'output/' # path to the output data
name_list['thresholds'] = [20,30,40] # in dbz
name_list['min_cluster_size'] = [10,5,3] # in number of points per cluster
name_list['operator'] = '>=' # '>= - <=' or '=='
name_list['timestamp_pattern'] = '%Y%m%d_%H%M%S.nc' # timestamp file pattern
name_list['delta_time'] = 12 # in minutes
name_list['edges'] = True # True or False for edge detection
name_list['x_dim'] = 241 # number of points in x
name_list['y_dim'] = 241 # number of points in y
name_list['lon_min'] = -62.1475 # Min longitude of data in degrees
name_list['lon_max'] = -57.8461 # Max longitude of data in degrees
name_list['lat_min'] = -5.3048 # Min latitude of data in degrees
name_list['lat_max'] = -0.9912 # Max latitude of data in degrees
name_list['spl_correction'] = True # Set to True to apply the Split correction
name_list['mrg_correction'] = True # Set to True to apply the Merge correction
name_list['inc_correction'] = True # Set to True to apply the Inner Cores correction
name_list['opt_correction'] = True # Set to True to apply the Optical Flow correction
name_list['opt_mtd'] = 'farneback' # 'farnerback' or 'lucas_kanade'
name_list['elp_correction'] = True # Set to True to apply the Ellipse correction
name_list['validation'] = True # Set to True to apply the validation of corrections
name_list['validation_scores'] = True  # Set to True to get the scores of the validation
name_list['pattern_position'] = [0,100]

if __name__ == '__main__':
    # Download example data and unzip to input folder
    url = 'https://zenodo.org/api/records/10624391/files-archive'
    response = requests.get(url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        zip_ref.extractall('input')
    # Run pyfortracc
    print('pyFortracc version', pyfortracc.__version__)
    pyfortracc.features_extraction(name_list, read_function, parallel=True)
    pyfortracc.spatial_operations(name_list, read_function, parallel=True)
    pyfortracc.cluster_linking(name_list)
    pyfortracc.concat(name_list, clean=True)
    pyfortracc.post_processing.compute_duration(name_list, parallel=True)
    pyfortracc.spatial_conversions(name_list, boundary=True, trajectory=True, vector_field=True,
                                   cluster=True, vel_unit='m/s', driver='GeoJSON')
    pyfortracc.plot(name_list=name_list, timestamp='2014-02-12 11:00:00',
                    read_function=read_function, cmap='viridis', num_colors=10, figsize=(10,10),
                    boundary=True, centroid=True, trajectory=True, threshold_list=[20,35,40],
                    vector=True, info=True, info_col_name=True, smooth_trajectory=True,
                    bound_color='red', bound_linewidth=1, centr_color='black', centr_size=1,
                    x_scale=0.1, y_scale=0.1, traj_color='blue', traj_linewidth=1, traj_alpha=0.8,
                    vector_scale=20, vector_color='black', info_cols=['uid','status', 'lifetime'],
                    save=True, save_path='output/', save_name='plot.png')
    tracking_files = sorted(glob.glob(name_list['output_path'] + '/track/trackingtable/*.parquet'))
    tracking_table = pd.concat(pd.read_parquet(f) for f in tracking_files)
    tracking_table.to_csv(name_list['output_path'] + '/track/tracking_table.csv')

