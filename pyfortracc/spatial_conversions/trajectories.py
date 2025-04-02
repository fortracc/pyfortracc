
import geopandas as gpd
import pathlib
from shapely.wkt import loads
from multiprocessing import Pool
from pyfortracc.utilities.utils import (get_parquets, get_loading_bar,
                                        set_nworkers, check_operational_system,
                                        read_parquet, create_dirs)

def trajectories(name_list, start_time, end_time, driver='GeoJSON', mode = 'track', parallel = True):
    """
    Translates and saves trajectory data from Parquet files within a specified time range.

    Parameters
    ----------
    name_list : dict
        A dictionary containing relevant information, including paths and geotransformation settings.
    start_time : str or pd.Timestamp
        The start of the time range to filter the data.
    end_time : str or pd.Timestamp
        The end of the time range to filter the data.
    driver : str, optional
        The file format driver to use when saving the output files. Default is 'GeoJSON'.
    mode : str, optional
        The mode to filter the data. Default is 'track'.

    Returns
    -------
    None
    """
    print('Translate -> Geometry -> Trajectory:')
    name_list, parallel = check_operational_system(name_list, parallel)
    parquets = get_parquets(name_list)
    parquets = parquets.loc[parquets['mode'] == mode]
    parquets = parquets.loc[start_time:end_time]
    parquets = parquets.groupby(parquets.index)
    loading_bar = get_loading_bar(parquets)
    n_workers = set_nworkers(name_list)
    out_path = name_list['output_path'] + mode + '/geometry/trajectory/'
    create_dirs(out_path)
    if parallel:
        with Pool(n_workers) as pool:
            for _ in pool.imap_unordered(translate_trajectory,
                                        [(out_path, driver, parquet)
                                        for _, parquet
                                        in enumerate(parquets)]):
                loading_bar.update(1)
        pool.close()
        pool.join()
    else:
        for _, parquet in enumerate(parquets):
            translate_trajectory((out_path, driver, parquet))
            loading_bar.update(1)
    loading_bar.close()


def translate_trajectory(args):
    """
    Translates and saves trajectory data after applying a geotransformation.

    Parameters
    ----------
    args : tuple
        A tuple containing the following elements:
        - geotran (list or tuple): The geotransformation parameters to apply to the geometries.
        - output_path (str): The directory path where the output file will be saved.
        - driver (str): The file format driver (e.g., 'GeoJSON') to use when saving the file.
        - parquet (pd.DataFrame): The data frame containing trajectory information.
    
    Returns
    -------
    None
    """
    output_path = args[0]
    driver = args[1]
    parquet = args[-1][1]
    parquet_file = parquet['file'].unique()[0]
    file_name = pathlib.Path(parquet_file).name.replace('.parquet', '.'+driver)
    # Open parquet file
    parquet = read_parquet(parquet_file, None).reset_index()
    # Set used columns for translate boundary
    columns = ['cindex','timestamp', 'uid', 'status', 'threshold']
    #Check if have more then one threshold, is true add column iuid
    if len(parquet['threshold'].unique()) > 1:
        columns.append('iuid')
        columns.insert(2, columns.pop(columns.index('iuid')))
    trajectories_ = parquet['trajectory']
    # Load geometry
    trajectories_ = trajectories_.apply(loads)
    # Select columns
    parquet = parquet[columns + ['trajectory']]
    if 'timestamp' in parquet.columns:
        parquet['timestamp'] = parquet['timestamp'].astype(str)
    if 'lifetime' in parquet.columns:
        parquet['lifetime'] = parquet['lifetime'].astype(str)
    parquet = gpd.GeoDataFrame(parquet)
    parquet['geometry'] = trajectories_
    parquet.to_file(output_path + file_name, driver=driver)
    return
