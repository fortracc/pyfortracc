import numpy as np
from pyfortracc.default_parameters import default_parameters
from pyfortracc.utilities.utils import (get_loading_bar, 
                                        set_operator, 
                                        set_schema,
                                        get_edges)
from pyfortracc.features_extraction import extract_features
from pyfortracc.spatial_operations import spatial_operation
import glob
import pandas as pd
import pathlib
# import matplotlib.pyplot as plt
# import matplotlib
import xarray as xr


# setting the backend to avoid issues with the display
# matplotlib.use('TkAgg')


def read_forecast_image(forecast_image_path):
    """
    Reads a forecast image from a NetCDF file and extracts the relevant data array.

    Parameters
    ----------
    forecast_image_path : str
        The file path to the NetCDF file containing the forecast image.

    Returns
    -------
    forecast_image : numpy.ndarray
        The extracted forecast image as a 2D NumPy array.
    """
    forecast_image = xr.open_dataarray(forecast_image_path).data[0, :, :]
    print(f"Shape --------->>>: {forecast_image.shape}")
    return forecast_image

def save_forecast_image(forecast_image, forecast_output_path, 
                        forecast_timestamp, name_list):
    """
    Saves a forecast image to a NetCDF file with appropriate metadata.

    Parameters
    ----------
    forecast_image : numpy.ndarray
        The 2D forecast image array to be saved.
    
    forecast_output_path : str
        The directory path where the forecast image will be saved.
    
    forecast_timestamp : datetime
        The timestamp associated with the forecast image, used for naming the output file.
    
    name_list : dict
        A dictionary containing geographic bounding box coordinates:
        - 'lon_min': Minimum longitude value.
        - 'lon_max': Maximum longitude value.
        - 'lat_min': Minimum latitude value.
        - 'lat_max': Maximum latitude value.

    Returns
    -------
    forecast_filename : str
        The full path to the saved NetCDF file.
    """
    LON_MIN = name_list['lon_min']
    LON_MAX = name_list['lon_max']
    LAT_MIN = name_list['lat_min']
    LAT_MAX = name_list['lat_max']
    forecast_output_path = f"{forecast_output_path}images"
    pathlib.Path(forecast_output_path).mkdir(parents=True, exist_ok=True)
    forecast_filename = f"{forecast_output_path}/{forecast_timestamp.strftime('%Y%m%d_%H%M%S.nc')}"

    lon = np.linspace(LON_MIN, LON_MAX, forecast_image.shape[1])
    lat = np.linspace(LAT_MIN, LAT_MAX, forecast_image.shape[0])
    # Create xarray
    data_xarray = xr.DataArray(forecast_image,
                            coords=[lat, lon],
                            dims=['lat', 'lon'])
    # Add dimension time
    data_xarray = data_xarray.expand_dims({'time': [forecast_timestamp]})
    data_xarray.name = "Forecast"
    data_xarray.attrs["_FillValue"] = 0
    data_xarray.attrs["units"] = "1"
    data_xarray.attrs["long_name"] = "Forecast image"
    data_xarray.attrs["standard_name"] = "Forecast"
    data_xarray.attrs["crs"] = "EPSG:4326"
    data_xarray.attrs["description"] = "This is an forecast from pyfortracc extrapolation-based"
    data_xarray.to_netcdf(forecast_filename,
                        encoding={'Forecast': {'zlib': True,
                                                'complevel': 5}})
    return forecast_filename


def forecast(name_list, read_function):
    """
    Generate a forecast based on the input tracking data and save the forecast images.

    Parameters
    ----------
    name_list : dict
        A dictionary containing various parameters and configurations needed for forecasting.
        
    read_function : function
        Function used to read the image data from the tracking files.

    Steps
    -----
    1. Set up default parameters and paths for output.
    2. Validate if enough files are available for forecasting.
    3. Iterate over each time step to create and save forecast images.
    4. Perform spatial operations on the forecasted data.

    Returns
    -------
    None
    """
    name_list = default_parameters(name_lst=name_list)
    output_path = name_list['output_path']
    previous_time = name_list['previous_time']
    forecast_time = name_list['forecast_time']
    forecast_output_path = f"{output_path}forecast"
    forecast_timestamp = pd.to_datetime(name_list['forecast_timestamp'])
    time_delta = pd.to_timedelta(name_list['delta_time'], unit='m')
    
    operator = set_operator(name_list['operator'])
    f_schema = set_schema('features', name_list)
    s_schema = set_schema('spatial', name_list)
    l_schema = set_schema('linked', name_list)
    

    # Checking if the output path exists
    if not pathlib.Path(output_path):
        print('Output path does not exist')
        return
    
    track_files = sorted(glob.glob(f"{output_path}track/trackingtable/*.parquet"))

    for i, file in enumerate(track_files):
        file = file.split('/')[-1]
        if file == forecast_timestamp.strftime('%Y%m%d_%H%M.parquet'):
            break
    track_files = track_files[:i+1]

    if track_files.__len__() < name_list['previous_time']:
        print('Not enough files to forecast')
        return
    
    # creating the forecast output path if it does not exist
    forecast_output_path = f"{forecast_output_path}/{forecast_timestamp.strftime('%Y%m%d_%H%M')}/"
    pathlib.Path(forecast_output_path).mkdir(parents=True, exist_ok=True)

    track_files = track_files[-previous_time:]    
    loading_bar = get_loading_bar(track_files)

    print("Forecasting:")

    tracking_table = pd.concat([pd.read_parquet(file) for file in track_files])
    # for each NaN in iuid, fill with uid
    tracking_table['iuid'] = tracking_table['iuid'].fillna(tracking_table['uid'])

#    print(tracking_table[['timestamp', 'uid', 'iuid', 'threshold_level', 'u_', 'v_', 'array_y', 'array_x']])
    print(tracking_table[['timestamp', 'uid', 'iuid', 'threshold_level', 'u_', 'v_']])
    last_image = read_function(tracking_table.file.unique()[-1])
    
    if len(name_list['thresholds']) > 1:
        group_columns = ['threshold_level', 'uid', 'iuid']
    else:
        group_columns = ['threshold_level', 'uid']

    left_edge, right_edge = get_edges(name_list['edges'], track_files, read_function)
    print(tracking_table.columns)
    for i in range(forecast_time):
        forecast_timestamp += time_delta

        print(f"Forecasting time step {i+1}")
        print(f"Forecasting time: {forecast_timestamp}")
        forecast_image = np.full((name_list['y_dim'], name_list['x_dim']), np.nan)

        cluster_groups = tracking_table.groupby(group_columns)

        for name, group in cluster_groups:
            # checking if all u_ and v_ are NaN
            if group.u_.isna().all() or group.v_.isna().all():
                continue
            
            # calculating mean u_ and v_, ignoring NaN
            avg_u = group.u_.mean(skipna=True)
            avg_v = group.v_.mean(skipna=True)
            
            # getting array list from tracking table
            array_indexes_x = group.iloc[-1]['array_x']
            array_indexes_y = group.iloc[-1]['array_y']

            # extrapolating the array indexes
            new_array_indexes_x = np.ceil(array_indexes_x + avg_u).astype(int)
            new_array_indexes_y = np.ceil(array_indexes_y + avg_v).astype(int)

            # checking if the new indexes are within the image
            new_array_indexes_x = np.clip(new_array_indexes_x, 0, name_list['x_dim'] - 1)
            new_array_indexes_y = np.clip(new_array_indexes_y, 0, name_list['y_dim'] - 1)

            array_values = last_image[array_indexes_y, array_indexes_x]

            # updating the forecast image
            forecast_image[new_array_indexes_y, new_array_indexes_x] = array_values

        # extract features from the forecast image
        
        # save forecast image
        forecast_filename = save_forecast_image(forecast_image, forecast_output_path, forecast_timestamp, name_list)

        name_list['input_path'] = forecast_output_path
        name_list['output_path'] = forecast_output_path
        name_list['output_features'] = f"{forecast_output_path}/features/"
        name_list['output_spatial'] = f"{forecast_output_path}/spatial/"
        pathlib.Path(name_list['output_features']).mkdir(parents=True, exist_ok=True)
        pathlib.Path(name_list['output_spatial']).mkdir(parents=True, exist_ok=True)

        extract_features((forecast_filename, name_list, operator, read_forecast_image, f_schema))
        cur_file = name_list['output_features'] + f"{forecast_timestamp.strftime('%Y%m%d_%H%M.parquet')}"
        cur_file = cur_file.replace("//", '/')
        if i == 0:
            prv_file = track_files[-1]
        else:
            prv_file = name_list['output_features'] + f"{(forecast_timestamp-time_delta).strftime('%Y%m%d_%H%M.parquet')}"
        prv_files = track_files[-1 :] #[track_files[-2], track_files[-1]]
        # print("\n\n\n\n\n\n")
        # print(f"cur_file: {cur_file}")
        # print(f"prv_file: {prv_file}")
        print(f"prv_files:")
        # for f in prv_files:
        #     print(f)
        # print("\n\n\n\n\n\n")
        # exit(0)
        print(f"prv_file: {prv_files}")
        spatial_operation((
            -1, 
            cur_file,
            [prv_file],
            prv_files,
            name_list,
            left_edge,
            right_edge,
            read_function,
            s_schema,
            True
        ))
        #(time_, cur_file, prv_file, prv_files, nm_lst, \
    #l_edge, r_edg, read_fnc, schm) = args

        break

    
# """
#     fig, ax = plt.subplots(1, 2, figsize=(20, 7), sharex=True, sharey=True)
#     ax[0].imshow(last_image, origin='lower')
#     ax[0].set_title('Last Image')
#     ax[0].grid(ls='--', c='k', lw=0.5)

#     ax[1].imshow(forecast_image, origin='lower')
#     ax[1].set_title('Forecast Image')
#     ax[1].grid(ls='--', c='k', lw=0.5)

#     plt.show()
# """
# # TODO: Implement forecast
# '''
# - Calculate dilatation and erosion.
# - Extrapolate values of the cluster to the forecasted time.
# - Consider the image boundaries in the full grid.
# '''