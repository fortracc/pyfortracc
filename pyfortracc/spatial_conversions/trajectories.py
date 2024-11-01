
import geopandas as gpd
from shapely.wkt import loads
from shapely.affinity import affine_transform
from multiprocessing import Pool
from pyfortracc.utilities.utils import (get_parquets, get_loading_bar,
                                        set_nworkers, get_geotransform,
                                        read_parquet, create_dirs)

def trajectories(name_list, start_time, end_time, driver='GeoJSON', mode = 'track'):
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
    parquets = get_parquets(name_list)
    parquets = parquets.loc[parquets['mode'] == mode]
    parquets = parquets.loc[start_time:end_time]
    parquets = parquets.groupby(parquets.index)
    loading_bar = get_loading_bar(parquets)
    geo_transf, _ = get_geotransform(name_list)
    n_workers = set_nworkers(name_list)
    out_path = name_list['output_path'] + mode + '/geometry/trajectory/'
    create_dirs(out_path)
    with Pool(n_workers) as pool:
        for _ in pool.imap_unordered(translate_trajectory,
                                    [(geo_transf, out_path, driver, parquet)
                                    for _, parquet
                                    in enumerate(parquets)]):
            loading_bar.update(1)
    pool.close()
    pool.join()
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
    geotran = args[0]
    output_path = args[1]
    driver = args[2]
    parquet = args[-1][1]
    parquet_file = parquet['file'].unique()[0]
    file_name = parquet_file.split('/')[-1].replace('.parquet', '.'+driver)
    # Open parquet file
    parquet = read_parquet(parquet_file, None).reset_index()
    # Set used columns for translate boundary
    columns = ['cindex','timestamp', 'uid', 'iuid', 'status', 'threshold']
    trajectories_ = parquet['trajectory']
    # Load geometry
    trajectories_ = trajectories_.apply(loads)
    # Transform geometry
    parquet['trajectory'] = trajectories_.apply(lambda x:
                                                affine_transform(x, geotran))
    # Select columns
    parquet = parquet[columns + ['trajectory']]
    if 'timestamp' in parquet.columns:
        parquet['timestamp'] = parquet['timestamp'].astype(str)
    if 'lifetime' in parquet.columns:
        parquet['lifetime'] = parquet['lifetime'].astype(str)
    parquet = gpd.GeoDataFrame(parquet, geometry='trajectory')
    parquet.to_file(output_path + file_name, driver=driver)
    return
