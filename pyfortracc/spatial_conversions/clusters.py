import numpy as np
import xarray as xr
import pandas as pd
import pathlib
from multiprocessing import Pool
from pyfortracc.utilities.utils import (get_parquets, get_loading_bar,
                                        set_nworkers, check_operational_system,
                                        create_dirs, get_featstamp)
from pyfortracc.default_parameters import default_parameters


def clusters(name_list, start_time, end_time, read_function, mode='track', cmp_lvl=9, parallel=True):
    """
    This function processes a series of parquet files containing geospatial tracking data to generate clusters.
    The processed clusters are saved to an output directory.

    Parameters
    -------
    - name_list: list
        A dictionary or object containing various configuration settings and paths needed for processing.
    - start_time: time
        The start of the time range for filtering parquet files.
    - end_time: time
        The end of the time range for filtering parquet files.
    - mode: str, optional
        A string indicating the mode of the data to be processed (default is 'track').
    - cmp_lvl: int, optional
        An integer value representing the compression level for output files (default is 9).

    Returns
    -------
    None    
    """
    print('Translate -> Cluster:')
    name_list = default_parameters(name_list, read_function)
    name_list, parallel = check_operational_system(name_list, parallel)
    parquets = get_parquets(name_list)
    parquets = parquets.loc[parquets['mode'] == mode]
    parquets = parquets.loc[start_time:end_time]
    parquets = parquets.groupby(parquets.index)
    loading_bar = get_loading_bar(parquets)
    n_workers = set_nworkers(name_list)
    out_path = name_list['output_path'] + mode + '/clusters/'
    create_dirs(out_path)
    if parallel:
        with Pool(n_workers) as pool:
            for _ in pool.imap_unordered(translate_cluster,
                                        [(out_path, parquet,
                                        cmp_lvl, name_list)
                                        for _, parquet in enumerate(parquets)]):
                loading_bar.update(1)
        pool.close()
        pool.join()
    else:
        for _, parquet in enumerate(parquets):
            translate_cluster((out_path, parquet, cmp_lvl, name_list))
            loading_bar.update(1)
    loading_bar.close()


def translate_cluster(args):
    """
    This function processes a parquet file to extract and organize cluster data, which is then saved as a NetCDF file.

    Parameters
    -------
    args: tuple
        A tuple containing multiple elements:
        1. output_path: The directory path where the resulting NetCDF file will be saved.
        2. parquet: The parquet file data, including relevant columns for processing.
        3. cmp_lvl: The compression level for the output NetCDF file.
        4. n_list: A dictionary or object containing various configuration settings, such as thresholds and grid dimensions.

    Returns
    -------
    None
    
    Description
    -------
    The function does not return a value but saves the processed cluster data as a compressed NetCDF file in the specified output directory.
    """
    output_path = args[0]
    parquet = args[1][1]
    cmp_lvl = args[2]
    n_list = args[-1]
    parquet_file = parquet['file'].unique()[0]
    file_name = pathlib.Path(parquet_file).stem
    timestamp = get_featstamp(parquet_file)
    parquet = pd.read_parquet(parquet_file, columns=['uid', 'iuid', 'threshold_level',
                                                     'array_y', 'array_x'])
    # Get shape and mount zeros array
    shape = (len(n_list['thresholds']), n_list['y_dim'], n_list['x_dim'])
    array = np.full(shape, 0, dtype=float)
    for i, row in parquet.iterrows():
        if row['threshold_level'] == 0:
            level = int(row['threshold_level'])
            values = row['uid']
        else:
            level = int(row['threshold_level'])
            values = row['iuid']
        y_coords = row['array_y']
        x_coords = row['array_x']
        array[level, y_coords, x_coords] = values
    # Create longitude and latitude array
    LON_MIN = n_list['lon_min']
    LON_MAX = n_list['lon_max']
    LAT_MIN = n_list['lat_min']
    LAT_MAX = n_list['lat_max']
    lon = np.linspace(LON_MIN, LON_MAX, array.shape[-1])
    lat = np.linspace(LAT_MIN, LAT_MAX, array.shape[-2])
    # Create xarray
    data_xarray = xr.DataArray(array,
                            coords=[np.arange(array.shape[0]),
                                    lat, lon],
                            dims=['threshold-level', 'lat', 'lon'])
    # Add dimension time
    data_xarray = data_xarray.expand_dims({'time': [timestamp]})
    data_xarray.name = "Clusters"
    data_xarray.attrs["_FillValue"] = 0
    data_xarray.attrs["units"] = "1"
    data_xarray.attrs["long_name"] = "Cluster"
    data_xarray.attrs["standard_name"] = "Cluster ID"
    data_xarray.attrs["crs"] = "EPSG:4326"
    data_xarray.attrs["description"] = "This is an output from pyfortracc"
    data_xarray.to_netcdf(output_path + file_name + '.nc',
                           encoding={'Clusters': {'zlib': True, 'complevel': cmp_lvl}})

    return
