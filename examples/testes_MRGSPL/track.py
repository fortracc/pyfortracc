import sys
sys.path.append("../../")
import pyfortracc
import numpy as np
import xarray as xr
def avg_intrp(X, d=1):
    """
    Interpolate NaN values in a 2D array using a moving window average.

    Args:
    X (numpy.ndarray): 2D input array with potential NaN values
    d (int): Size of the averaging window (default is 1)

    Returns:
    numpy.ndarray: Array with NaN values interpolated
    """
    # Create a copy of the input array to avoid modifying the original
    X = X.copy()

    # Find indices of NaN values
    bad_idx = np.argwhere(np.isnan(X))

    # Get dimensions of the array
    dim = X.shape

    # Create padded array
    row_pad = np.full((d, dim[1] + (2*d)), np.nan)
    col_pad = np.full((dim[0], d), np.nan)
    pad_X = np.pad(X, ((d, d), (d, d)), mode='constant', constant_values=np.nan)

    # Interpolate NaN values
    for idx in bad_idx:
        row, col = idx
        row_idx = slice(row, row + 2*d + 1)
        col_idx = slice(col, col + 2*d + 1)

        # Extract the window
        window = pad_X[row_idx, col_idx]

        # Calculate mean of non-NaN values
        valid_vals = window[~np.isnan(window)]
        if len(valid_vals) > 0:
            X[row, col] = np.mean(valid_vals)

    # Recursive interpolation if a small percentage of NaNs remain
    nan_ratio = np.sum(np.isnan(X)) / X.size
    if 0 < nan_ratio <= 0.05:
        X = avg_intrp(X, d)

    return X
def read_merg_ir(path):
    """
    Reads MERGIR data from a NetCDF file, extracting brightness temperature data.
    Args:
        path (str): Path to the MERGIR NetCDF file.
    Returns:
        numpy.ndarray: A 2D NumPy array containing the brightness temperature data
                         with dimensions (latitude, longitude). Returns the 'Tb' variable
                         inverted in the latitude dimension.
    """
    MERGIR_data = xr.open_dataset(path)
    brightness_temp = MERGIR_data['Tb'].values
    # Interpolate NaNs
    data_interpolated = avg_intrp(brightness_temp)
    return data_interpolated[::-1]
ds = xr.open_dataset("interpolated/202002250000.nc")

# Get the lon_min, lon_max, lat_min and lat_max of the domain
lon_min = float(ds['lon'].min().values)
lon_max = float(ds['lon'].max().values)
lat_min = float(ds['lat'].min().values)
lat_max = float(ds['lat'].max().values)

# Initialize an empty dictionary for the namelist
name_list = {}
name_list['input_path'] = 'interpolated/'
name_list['output_path'] = 'output/'

# Set features name list
name_list['thresholds'] = [235]
name_list['min_cluster_size'] = [150]
name_list['operator'] = '<='
name_list['timestamp_pattern'] = '%Y%m%d%H%M.nc'
name_list['delta_time'] = 30
name_list['cluster_method'] = 'ndimage'
name_list['edges'] = True

# Add correction methods
name_list['spl_correction'] = True # It is used to perform the correction at Splitting events
name_list['mrg_correction'] = True # It is used to perform the correction at Merging events

# Set min overlap percentage
name_list['min_overlap'] = 5

# Spatial parameters
name_list['lon_min'] = lon_min # Set the lon_min
name_list['lon_max'] = lon_max # Set the lon_max
name_list['lat_min'] = lat_min # Set the lat_min
name_list['lat_max'] = lat_max # Set the lat_max


# pyfortracc.features_extraction(name_list, read_merg_ir)
pyfortracc.spatial_operations(name_list, read_merg_ir, parallel=False)
# pyfortracc.cluster_linking(name_list)
# pyfortracc.concat(name_list, clean=False)
