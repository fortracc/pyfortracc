import pandas as pd
import pathlib
import numpy as np
import xarray as xr
from pyfortracc.default_parameters import default_parameters
from pyfortracc.utilities.utils import get_feature_files, \
                                        save_netcdf, \
                                        set_operator, \
                                        set_schema, \
                                        get_edges, \
                                        get_geotransform
from pyfortracc.features_extraction import extract_features
from pyfortracc.spatial_operations import spatial_operation

def forecast(name_list, read_function):
    """
    Generate a forecast based on the input tracking data and save the forecast images.

    Parameters
    ----------
    name_list : dict
        A dictionary containing various parameters and configurations needed for forecasting.
        
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

    # Verify if have necessary parameters for forecasting, with is forecast_time, observation_window and lead_time
    if 'forecast_time' not in name_list or \
       'observation_window' not in name_list or \
       'lead_time' not in name_list:
        print("Missing parameters for forecasting. Please provide 'forecast_time', 'observation_window', and 'lead_time'.")
        return

    # Set default parameters if not provided
    name_list = default_parameters(name_lst=name_list, 
                                   read_function=read_function)
    
    # Get track files from the output path
    tracked_files = get_feature_files(name_list['output_path'] + 'track/trackingtable/',
                                      name_list=name_list)
    # Set forecast parameters
    last_timestamp = pd.to_datetime(name_list['forecast_time'])
    delta_time = pd.to_timedelta(name_list['delta_time'], unit='m')
    forecast_times = pd.date_range(start=last_timestamp + delta_time,
                                   periods=name_list['lead_time'],
                                   freq=delta_time)
    # Set output path for forecast images
    forecast_output = name_list['output_path'] + 'forecast/'

    # Set variables used in tracking
    operator = set_operator(name_list['operator'])
    f_schema = set_schema('features', name_list)
    s_schema = set_schema('spatial', name_list)
    l_schema = set_schema('linked', name_list)
    left_edge, right_edge = get_edges(name_list, 
                                      tracked_files, 
                                      read_function)
    geo_transf = get_geotransform(name_list)
    
    # Set readfunction based on lat_min, lat_max, lon_min, lon_max
    if all(key in name_list and name_list[key] is not None for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
        def frcst_read_func(frcst_out):
            return xr.open_dataarray(frcst_out).data[0, :, :]
    else:
        def frcst_read_func(frcst_out):
            return np.load(frcst_out)

    # Get forecast mode function
    if name_list['forecast_mode'] == 'persistence':
        # import persistence_forecast as mode
        from pyfortracc.forecast.persistence import persistence as forecast_function
    else:
        print(f"Forecast mode {name_list['forecast_mode']} not implemented yet.")
        return
    
    print(f"Forecasting window: {last_timestamp} to {forecast_times[-1]}")
    # Loop through forecast times to create forecast output path
    for ftsmp in range(len(forecast_times)):
        
        # 1 - First Step of the forecast is create forecast image
        print(f"- Generating forecast image lead time +{ftsmp + 1}: {forecast_times[ftsmp]}")
        forecast_img = forecast_function(tracked_files, name_list)
        
        # Saving the forecast image
        frcst_out = forecast_output
        frcst_out += f"{last_timestamp.strftime('%Y%m%d_%H%M')}/"
        frcst_out += 'forecast_images/'
        pathlib.Path(frcst_out).mkdir(parents=True, exist_ok=True)
        
        # Check if name_list have lat_min, lat_max, lon_min, lon_max is different from None
        if all(key in name_list and name_list[key] is not None for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
            frcst_file = f"{forecast_times[ftsmp].strftime('%Y%m%d_%H%M%S.nc')}"
            # Save as a netCDF file
            save_netcdf(forecast_img, name_list, frcst_out + frcst_file)
            # Update name_list with timestamp pattern for netCDF
            name_list['timestamp_pattern'] = '%Y%m%d_%H%M%S.nc'
        else:
            # Save as a numpy file
            frcst_file = f"{forecast_times[ftsmp].strftime('%Y%m%d_%H%M%S.npy')}"
            np.save(frcst_out, frcst_out + frcst_file)
            # Update name_list with timestamp pattern for numpy
            name_list['timestamp_pattern'] = '%Y%m%d_%H%M%S.npy'


        # 2 - Second Step of the forecast is extract features from the forecast image
        print(f"- Extracting features from forecast image lead time +{ftsmp + 1}: {forecast_times[ftsmp]}")
  
        # Update name_list with forecast information
        name_list['input_path'] = frcst_out
        name_list['output_path'] = forecast_output + f"{last_timestamp.strftime('%Y%m%d_%H%M')}/"
        name_list['output_features'] = f"{name_list['output_path']}features/"
        pathlib.Path(name_list['output_features']).mkdir(parents=True, exist_ok=True)
 
        # Extract features
        extract_features((frcst_out + frcst_file, 
                          name_list, 
                          operator, 
                          frcst_read_func, 
                          f_schema))

        # 3 - Third Step of the forecast is perform spatial operations on the forecasted data
        print(f"- Performing spatial operations on forecast image lead time +{ftsmp + 1}: {forecast_times[ftsmp]}")

        # Update name_list with forecast information
        name_list['output_spatial'] = f"{name_list['output_path']}spatial/"
        pathlib.Path(name_list['output_spatial']).mkdir(parents=True, exist_ok=True)

        # Get the current forecast file
        cur_file = name_list['output_features'] + f"{forecast_times[ftsmp].strftime('%Y%m%d_%H%M')}.parquet"
        prv_file = tracked_files[-1] # Use the last tracked file as previous file
        prv_files = tracked_files[-1:]  # Use the last tracked file as previous files
        # Perform spatial operations
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
                          True,
                          geo_transf
                          ))
        exit()

    # output_path = name_list['output_path']
    # previous_time = name_list['previous_time']
    # forecast_time = name_list['forecast_time']
    # forecast_output_path = f"{output_path}forecast"
    # forecast_timestamp = pd.to_datetime(name_list['forecast_timestamp'])
    # time_delta = pd.to_timedelta(name_list['delta_time'], unit='m')
    
    # operator = set_operator(name_list['operator'])
    # f_schema = set_schema('features', name_list)
    # s_schema = set_schema('spatial', name_list)
    # l_schema = set_schema('linked', name_list)
    

    # # Checking if the output path exists
    # if not pathlib.Path(output_path):
    #     print('Output path does not exist')
    #     return
    
    # track_files = sorted(glob.glob(f"{output_path}track/trackingtable/*.parquet"))
    # print(track_files)
    # exit()

    