
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
name_list['thresholds'] = [20,30,35] # in dbz
name_list['min_cluster_size'] = [3,3,3] # in number of points per cluster
name_list['operator'] = '>=' # '>= *   **<=' or '=='
name_list['delta_time'] = 12 # in minutes
name_list['min_overlap'] = 20 # Minimum overlap between clusters in percentage

# Not mandatory parameters, if not set, the algorithm will use the default values
name_list['track_start'] = '2014-08-16 11:00:00' # Start time of the tracking in UTC
name_list['track_end'] = '2014-08-16 14:00:00' # End time of the tracking in UTC
#TODO

# Optional parameters, if not set, the algorithm will not use geospatial information
name_list['lon_min'] = -62.1475 # Min longitude of data in degrees
name_list['lon_max'] = -57.8461 # Max longitude of data in degrees
name_list['lat_min'] = -5.3048 # Min latitude of data in degrees
name_list['lat_max'] = -0.9912 # Max latitude of data in degrees

name_list['forecast_time'] = '2014-08-16 14:00:00'
name_list['observation_window'] = 5 # Number of previous images
name_list['lead_time'] = 3 # Amount of time to forecast

name_list['edges'] = True # If True, the edges of the clusters will be considered in the tracking


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

    pyfortracc.forecast(name_list, read_function)
