import geopandas as gpd
import pathlib
from shapely.wkt import loads
from shapely.affinity import affine_transform
from multiprocessing import Pool
from pyfortracc.utilities.utils import (get_parquets, get_loading_bar,
                                        set_nworkers, check_operational_system,
                                        read_parquet, create_dirs)


def vectorfield(name_list, start_time, end_time, driver='GeoJSON', mode = 'track', parallel = True):
    """
    Translates and saves vector field data from Parquet files within a specified time range.

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
        The mode to filter the data by. Default is 'track'.

    Returns
    -------
    None
    """    
    print('Translate -> Geometry -> Vector Field:')
    name_list, parallel = check_operational_system(name_list, parallel)
    parquets = get_parquets(name_list)
    parquets = parquets.loc[parquets['mode'] == mode]
    parquets = parquets.loc[start_time:end_time]
    parquets = parquets.groupby(parquets.index)
    loading_bar = get_loading_bar(parquets)
    n_workers = set_nworkers(name_list)
    out_path = name_list['output_path'] + mode + '/geometry/vector_field/'
    create_dirs(out_path)
    if parallel:
        with Pool(n_workers) as pool:
            for _ in pool.imap_unordered(translate_vfield,
                                        [(out_path, driver, parquet)
                                        for _, parquet
                                        in enumerate(parquets)]):
                loading_bar.update(1)
        pool.close()
        pool.join()
    else:
        for _, parquet in enumerate(parquets):
            translate_vfield((out_path, driver, parquet))
            loading_bar.update(1)
    loading_bar.close()


def translate_vfield(args):
    """
    Translates and saves vector field data from a Parquet file to a specified format, applying geotransformations.

    Parameters
    ----------
    args : tuple
        A tuple containing the following elements:
        - geotran : list or array
            The geotransformation parameters to apply to the vector field geometries.
        - output_path : str
            The directory path where the output files will be saved.
        - driver : str
            The file format driver (e.g., 'GeoJSON') to use when saving the output files.
        - parquet : pd.DataFrame
            A DataFrame containing the data to be translated, with vector field geometries and other columns.

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
    columns = ['cindex','timestamp','uid','iuid','status','threshold']
    # Load geometry
    parquet['vector_field'] = parquet['vector_field'].apply(loads)
    # Select columns
    parquet = parquet[columns + ['vector_field']]
    if 'timestamp' in parquet.columns:
        parquet['timestamp'] = parquet['timestamp'].astype(str)
    if 'lifetime' in parquet.columns:
        parquet['lifetime'] = parquet['lifetime'].astype(str)
    parquet = gpd.GeoDataFrame(parquet)
    parquet['geometry'] = parquet['vector_field']
    parquet.to_file(output_path + file_name, driver=driver)
    return

