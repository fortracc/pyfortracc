import geopandas as gpd
import pandas as pd
import pathlib
from shapely.wkt import loads
from shapely.affinity import affine_transform
from multiprocessing import Pool
from pyfortracc.utilities.utils import (get_parquets, get_loading_bar,
                                        set_nworkers, check_operational_system,
                                        read_parquet, create_dirs)
from pyfortracc.utilities.math_utils import uv2angle, uv2magn, calculate_vel_area



def boundaries(name_list, start_time, end_time, 
                vel_unit = 'km/h', driver='GeoJSON', mode = 'track', parallel = True):
    """
    This function processes geospatial tracking data to extract and translate boundaries of tracked objects 
    within a specified time range, then saves the boundaries in a specified format.
    
    Parameters
    -------
    - name_list: dict
        A dictionary containing configuration information, including paths and settings.
    - start_time: str or pd.Timestamp
        The start of the time range for which data should be processed.
    - end_time: str or pd.Timestamp
        The end of the time range for which data should be processed.
    - vel_unit: str, optional
        The unit of velocity for the output data (default is 'km/h').
    - driver: str, optional
        The format/driver for saving the output boundaries (default is 'GeoJSON').
    - mode: str, optional
        The mode of operation, which typically specifies the type of data to process (default is 'track').
    
    Returns
    -------
    None
    """
    print('Translate -> Geometry -> Boundary:')
    name_list, parallel = check_operational_system(name_list, parallel)
    parquets = get_parquets(name_list)
    parquets = parquets.loc[parquets['mode'] == mode]
    parquets = parquets.loc[start_time:end_time]
    parquets = parquets.groupby(parquets.index)
    loading_bar = get_loading_bar(parquets)
    # geo_transf, _ = get_geotransform(name_list)
    n_workers = set_nworkers(name_list)
    out_path = name_list['output_path'] + mode +  '/geometry/boundary/'
    # pixel_area, xlat, xlon = calculate_pixel_area(name_list)
    pixel_area, xlat, xlon = None, None, None
    delta_time = name_list['delta_time']
    create_dirs(out_path)
    if parallel:
        with Pool(n_workers) as pool:
            for _ in pool.imap_unordered(translate_boundary,
                                        [(vel_unit,
                                        out_path, driver, parquet, 
                                        pixel_area, xlat, xlon, delta_time)
                                        for _, parquet
                                        in enumerate(parquets)]):
                loading_bar.update(1)
        pool.close()
        pool.join()
    else:
        for _, parquet in enumerate(parquets):
            translate_boundary((vel_unit, out_path, driver, parquet, pixel_area, xlat, xlon, delta_time))
            loading_bar.update(1)
    loading_bar.close()


def translate_boundary(args):
    """
    This function processes a single parquet file containing geospatial tracking data to calculate 
    velocity and angle vectors, transform geometries, and save the processed data in a specified format.

    Parameters
    -------
    - args: list
        A list or tuple containing the following elements:
        1. geotran: A geotransformation matrix used to transform the geometries.
        2. vel_unit: The unit of velocity for the output data (e.g., 'km/h').
        3. output_path: The path where the processed file will be saved.
        4. driver: The format/driver for saving the output file (e.g., 'GeoJSON').
        5. parquet: The parquet data to be processed.
    
    Returns
    -------
    None
    
    Description
    -------
    The function does not return a value but saves the processed data with transformed geometries, 
    calculated velocity and angle vectors, and selected columns to a file in the specified format.
    """
    vel_unit = args[0]
    output_path = args[1]
    driver = args[2]
    parquet = args[3][1]
    pixel_area = args[4]
    xlat = args[5]
    xlon = args[6]
    delta_time = args[7]
    parquet_file = parquet['file'].unique()[0]
    file_name = pathlib.Path(parquet_file).name.replace('.parquet', '.'+driver)
    # Open parquet file
    parquet = read_parquet(parquet_file, None).reset_index()
    # Set used columns for translate boundary
    columns = ['timestamp','uid','status','threshold','size',
                'mean','std','min','max','lifetime','inside_clusters']
    #Check if have more then one threshold, is true add column iuid
    if len(parquet['threshold'].unique()) > 1:
        columns.append('iuid')
        columns.insert(2, columns.pop(columns.index('iuid')))
    # Check if have region or duration columns of parquet
    if 'region' in parquet.columns:
        columns.append('region')
    if 'duration' in parquet.columns:
        columns.append('duration')
    if 'expansion' in parquet.columns:
        columns.append('expansion')
    if 'board' in parquet.columns:
        columns.append('board')
    # Load geometry
    geometries = parquet['geometry'].apply(loads)
    centroids = geometries.apply(lambda x: x.centroid)
    parquet['centroid'] = centroids.apply(lambda x: x.y)
    parquet['clon'] = centroids.apply(lambda x: x.x)
    parquet['clat'] = centroids.apply(lambda x: x.y)
    # Get u and v columns
    uv_cols = [col for col in parquet.columns if col.startswith('u_') or
                                                col.startswith('v_')]
    # Set velocity and angle columns
    ang_vel_cols = []
    # Loop over two by two columns (u and v)
    for u_c, v_c in zip(uv_cols[::2], uv_cols[1::2]):
        # Convert uv to angle
        parquet['ang_' + u_c[2:]] = parquet[[u_c,v_c]].apply(lambda x:
                                                    uv2angle(x[u_c], x[v_c])
                                                    if not pd.isnull(x[u_c])
                                                    or not pd.isnull(x[v_c])
                                                    else None, axis=1)
        # TODO: Convert uv to magnitude and calculate velocity based on vel_unit
        # parquet['vel_' + u_c[2:]] =  parquet[[u_c,v_c,'clon','clat']].apply(lambda x:
        #                                             calculate_vel_area(
        #                                             uv2magn(x[u_c],x[v_c]),
        #                                             'km/h', 
        #                                             get_pixarea(x['clon'], 
        #                                                         x['clat'], 
        #                                                         xlon, 
        #                                                         xlat, 
        #                                                         pixel_area),
        #                                                         delta_time)
        #                                             if not pd.isnull(x[u_c])
        #                                             or not pd.isnull(x[v_c])
        #                                             else None, axis=1)
        # Append columns
        ang_vel_cols.append('ang_' + u_c[2:])
        # ang_vel_cols.append('vel_' + u_c[2:])
    
    # Select columns
    parquet = parquet[columns + ang_vel_cols + ['geometry']]
    if 'timestamp' in parquet.columns:
        parquet['timestamp'] = parquet['timestamp'].astype(str)
    if 'delta_time' in parquet.columns:
        parquet['delta_time'] = parquet['delta_time'].astype(str)
    if 'lifetime' in parquet.columns:
        parquet['lifetime'] = parquet['lifetime'].astype(str)
    parquet = gpd.GeoDataFrame(parquet)
    parquet['geometry'] = geometries
    parquet.to_file(output_path + file_name, driver=driver)
    return
