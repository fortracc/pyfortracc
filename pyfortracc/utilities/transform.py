import glob
import geopandas as gpd
import pandas as pd
import numpy as np
import pathlib
import xarray as xr
import multiprocessing as mp
from datetime import datetime
from shapely.wkt import loads
from shapely.ops import split
from shapely.affinity import translate
from shapely.geometry import MultiPolygon, LineString, MultiLineString
from tqdm import tqdm
from pyfortracc.utilities.utils import update_progress
import warnings
# Ignore warning UserWarning from geopandas
warnings.filterwarnings("ignore", category=UserWarning)

def geotransform(name_list, geometries=True, clusters=True, vector_field=True, trajectories=True, comp_lvl=3, geo_format='GeoJSON', parallel=True):
    """
    Transform the features in a trajectory and save them in specified formats. This function applies a geotransformation to various types of spatial data, including geometries, clusters, vector fields, and trajectories. It supports parallel processing for efficiency and handles the creation of necessary directories.

    Parameters
    ----------
    name_list : dict
        Dictionary containing configuration parameters, including:
        - 'output_path': Directory path for output files.
        - 'x_dim': X dimension for the geotransform.
        - 'y_dim': Y dimension for the geotransform.
        - 'n_jobs': Number of parallel jobs (if -1, use all available CPUs).
        - Additional keys for optional configurations and thresholds.
    geometries : bool, optional
        Whether to transform and save geometry features (default is True).
    clusters : bool, optional
        Whether to transform and save cluster features (default is True).
    vector_field : bool, optional
        Whether to transform and save vector field features (default is True).
    trajectories : bool, optional
        Whether to transform and save trajectory features (default is True).
    comp_lvl : int, optional
        Compression level for NetCDF output (default is 3).
    geo_format : str, optional
        Format for geometry output files (default is 'GeoJSON').
    parallel : bool, optional
        Whether to perform transformations in parallel (default is True).

    Returns
    -------
    None
    """
    if 'lat_min' not in name_list.keys() and 'lat_max' not in name_list.keys():
        print('Please set the lat_min and lat_max in the name_list')
        return
    elif 'x_dim' not in name_list.keys() and 'y_dim' not in name_list.keys():
        print('Please set the x_dim and y_dim in the name_list')
    # Set the geotransform
    X_DIM, Y_DIM = name_list['x_dim'], name_list['y_dim']
    geotransform, inv_geotransform = set_geotransform(name_list, Y_DIM, X_DIM) # Set the geotransform
    # Get the feature_files
    feature_files = sorted(glob.glob(name_list['output_path'] + 'features/*.parquet', recursive=True))
        # Create output directory for geometry files and clusters
    if geometries:
        pathlib.Path(name_list['output_path'] + 'geometry/boundary/').mkdir(parents=True, exist_ok=True)
    if trajectories:
        pathlib.Path(name_list['output_path'] + 'geometry/trajectory/').mkdir(parents=True, exist_ok=True)
    if vector_field:
        pathlib.Path(name_list['output_path'] + 'geometry/vector_field/').mkdir(parents=True, exist_ok=True)
    if clusters:
        pathlib.Path(name_list['output_path'] + 'clusters/').mkdir(parents=True, exist_ok=True)
    # Number of cores
    if 'n_jobs' not in name_list.keys():
        name_list['n_jobs'] = mp.cpu_count()
    elif name_list['n_jobs'] == -1:
        name_list['n_jobs'] = mp.cpu_count()
    # Parallel processing
    if parallel:
        pool = mp.Pool(name_list['n_jobs'])
        if geometries:
            print('Transforming the geometries features...')
            # Create the progress bar
            pbar = tqdm(total=len(feature_files), ncols=80, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [Elapsed:{elapsed} Remaining:<{remaining}]')
            # Pool of workers
            with mp.Pool(name_list['n_jobs']) as pool:
                for _ in pool.imap_unordered(to_geojson, [(feature_files[file],
                                                            name_list,
                                                            geotransform,
                                                            geometries,
                                                            trajectories,
                                                            vector_field,
                                                            geo_format) for file in range(len(feature_files))]):
                    # Update the progress bar
                    update_progress(1, pbar)        
            pbar.close()
        if clusters:
            print('Transforming the clusters features...')
            # Create the progress bar
            pbar = tqdm(total=len(feature_files), ncols=80, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [Elapsed:{elapsed} Remaining:<{remaining}]')
            # Pool of workers
            with mp.Pool(name_list['n_jobs']) as pool:
                for _ in pool.imap_unordered(to_netcdf, [(feature_files[file], name_list, comp_lvl) for file in range(len(feature_files))]):
                    # Update the progress bar
                    update_progress(1, pbar)
            # Close
            pbar.close()
        pool.close()
    else:
        if geometries:
            print('Transforming the geometries features...')
            # Create the progress bar
            pbar = tqdm(total=len(feature_files), ncols=80, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [Elapsed:{elapsed} Remaining:<{remaining}]')
            for file in range(len(feature_files)):
                to_geojson((feature_files[file], name_list, geotransform, geometries, trajectories, vector_field, geo_format))
                # Update the progress bar
                update_progress(1, pbar)
            # Close
            pbar.close()
        if clusters:
            print('Transforming the clusters features...')
            # Create the progress bar
            pbar = tqdm(total=len(feature_files), ncols=80, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [Elapsed:{elapsed} Remaining:<{remaining}]')
            for file in range(len(feature_files)):
                to_netcdf((feature_files[file], name_list, comp_lvl))
                # Update the progress bar
                update_progress(1, pbar)
            # Close
            pbar.close()
    
def set_geotransform(name_list, Y_DIM, X_DIM,):
    """
    Calculate the geotransform and its inverse for spatial data based on geographical bounds and dimensions.

    This function computes the geotransform matrix used for converting between pixel coordinates and geographical coordinates.
    It also calculates the inverse geotransform for reverse conversions.

    Parameters
    ----------
    name_list : dict
        Dictionary containing geographical bounds and other relevant parameters:
        - 'lon_min': Minimum longitude.
        - 'lon_max': Maximum longitude.
        - 'lat_min': Minimum latitude.
        - 'lat_max': Maximum latitude.
    Y_DIM : int
        Number of rows (pixels) in the spatial grid.
    X_DIM : int
        Number of columns (pixels) in the spatial grid.

    Returns
    -------
    tuple
        A tuple containing two elements:
        - geotransform : tuple
            The geotransform parameters in the form (xres, 0, 0, yres, LON_MIN, LAT_MIN).
        - geotransform_inv : tuple
            The inverse geotransform parameters in the form (xres_inv, 0, 0, yres_inv, LON_MIN_inv, LAT_MIN_inv).
    """
    LON_MIN = name_list['lon_min']
    LON_MAX = name_list['lon_max']
    LAT_MIN = name_list['lat_min']
    LAT_MAX = name_list['lat_max']
    # Calculate pixel size
    xres = abs(LON_MAX - LON_MIN) / X_DIM
    yres = abs(LAT_MAX - LAT_MIN) / Y_DIM
    # Transform matrix
    matrix = np.array([[xres, 0, LON_MIN], [0, yres, LAT_MIN], [0, 0, 1]])
    # Calculate geotransform
    geotransform = (matrix[0,0], matrix[0,1], matrix[1,0], matrix[1,1],matrix[0,2], matrix[1,2])
    # Calculate inverse matrix
    matrix_inv = np.linalg.inv(matrix)
    # Calculate inverse geotransform
    geotransform_inv = (matrix_inv[0,0], matrix_inv[0,1], matrix_inv[1,0], matrix_inv[1,1],matrix_inv[0,2], matrix_inv[1,2])
    return geotransform, geotransform_inv

def to_geojson(args):
    """
    Convert trajectory features stored in a Parquet file to GeoJSON format.

    This function reads spatial data from a Parquet file, applies geotransform if necessary, 
    and saves the data to GeoJSON files based on the specified types of features: 
    geometries, trajectories, vector fields, and optionally handles empty data.

    Parameters
    ----------
    args : tuple
        A tuple containing the following elements:
        - file : str
            Path to the input Parquet file.
        - name_list : dict
            Dictionary containing output paths and other configuration settings:
            - 'output_path': Directory path where output files will be saved.
            - 'lon_max': Maximum longitude (used for splitting geometries if greater than 180).
        - geotransform : tuple
            Geotransform parameters used for affine transformation of geometries.
        - geometries : bool
            Flag indicating whether to process and save geometries (e.g., boundaries).
        - trajectories : bool
            Flag indicating whether to process and save trajectories.
        - vector_field : bool
            Flag indicating whether to process and save vector field data.
        - drive : str
            File format driver to use for saving GeoJSON files (e.g., 'GeoJSON').

    Returns
    -------
    None
    """
    # Open the file
    file, name_list, geotransform, geometries, trajectories, vector_field, drive = args
    geo_frame = gpd.read_parquet(file)
    # Filename
    filename = pathlib.Path(file).stem
    # Check if the file is empty
    if geo_frame.empty:
        if geometries:
            geo_frame.to_file(name_list['output_path'] + 'geometry/boundary/' + filename + '.'+drive, driver=drive)
        if trajectories:
            geo_frame.to_file(name_list['output_path'] + 'geometry/trajectory/' + filename + '.'+drive, driver=drive)
        if vector_field:
            geo_frame.to_file(name_list['output_path'] + 'geometry/vector_field/' + filename + '.'+drive, driver=drive)
        return
    # Set the data type to string
    geo_frame["timestamp"] = geo_frame["timestamp"].astype(str)
    geo_frame["lifetime"] = geo_frame["lifetime"].astype(str)
    if geometries:
        # Set columns to geometry/boundary and trajectory
        boundary_columns = ['timestamp', 'uid','iuid','threshold','threshold_level', 'mean', 'std', 'min', 'Q1', 'Q2', 'Q3', 'max',
                            'size', 'inside_clusters', 
                            'dis_','dis_avg', 'dis_inc','dis_spl','dis_mrg','dis_opt', 
                            'dir_','dir_avg', 'dir_inc', 'dir_spl','dir_mrg', 'dir_opt',
                            'lifetime', 'status', 'board' ,'geometry', 'duration','region', 'centroid_distance']
        order_b_columns = [col for col in boundary_columns if col in geo_frame.columns]
        bound_frame = geo_frame[order_b_columns] # Boundary frame
        if 'duration' in bound_frame.columns:
            bound_frame['duration'] = bound_frame['duration'].astype(str)
        # Set the geometry to the boundary frame
        bound_frame = bound_frame.set_geometry('geometry')
        bound_frame['geometry'] = bound_frame['geometry'].affine_transform(geotransform)
        if name_list['lon_max'] > 180:
            bound_frame = split_lon_max(bound_frame, geotype=MultiPolygon)
        # Save to GeoJSON
        schema_ = gpd.io.file.infer_schema(bound_frame)
        bound_frame.to_file(name_list['output_path'] + 'geometry/boundary/' + filename + '.'+drive, driver=drive, schema=schema_)
    if trajectories:
        trajectory_columns = ['timestamp', 'uid','iuid','threshold','threshold_level', 
                            'dis_','dis_avg', 'dis_inc','dis_spl','dis_mrg','dis_opt', 
                            'dir_','dir_avg', 'dir_inc', 'dir_spl','dir_mrg', 'dir_opt',
                            'lifetime', 'status', 'trajectory']
        order_t_columns = [col for col in trajectory_columns if col in geo_frame.columns]
        traj_frame = geo_frame[order_t_columns] # Trajectory frame
        if 'trajectory' in traj_frame.columns:
            traj_frame['geometry'] = traj_frame['trajectory'].apply(lambda x: loads(x))
            traj_frame = gpd.GeoDataFrame(traj_frame, geometry='geometry')
            traj_frame['geometry'] = traj_frame['geometry'].affine_transform(geotransform)
            traj_frame = traj_frame.drop(columns=['trajectory'])
            if name_list['lon_max'] > 180:
                traj_frame = split_lon_max(traj_frame, geotype=MultiLineString)
            schema_ = gpd.io.file.infer_schema(traj_frame)
            # Save to GeoJSON
            traj_frame.to_file(name_list['output_path'] + 'geometry/trajectory/' + filename + '.'+drive, driver=drive, schema=schema_)
        else: # Create empty GeoDataFrame to save the timestamp
            traj_frame = gpd.GeoDataFrame(traj_frame)
            traj_frame['geometry'] = loads('LINESTRING EMPTY')
            # Save to GeoJSON
            traj_frame.to_file(name_list['output_path'] + 'geometry/trajectory/' + filename + '.'+drive, driver=drive)
        
    if vector_field:
        vectorfield_columns = ['timestamp', 'uid','iuid','threshold','threshold_level',
                            'dis_','dis_avg', 'dis_inc', 'dis_opt', 'dir_','dir_avg', 'dir_inc', 'dir_opt',
                                'lifetime', 'status', 'vector_field']    
        order_v_columns = [col for col in vectorfield_columns if col in geo_frame.columns]
        vec_frame = geo_frame[order_v_columns] # Vector field frame
        if 'vector_field' in vec_frame.columns:
            vec_frame = vec_frame.rename(columns={'vector_field': 'geometry'})
            vec_frame['geometry'] = vec_frame['geometry'].fillna('LINESTRING EMPTY')
            vec_frame['geometry'] = vec_frame['geometry'].apply(lambda x: loads(x))
            vec_frame = gpd.GeoDataFrame(vec_frame, geometry='geometry')
            vec_frame['geometry'] = vec_frame['geometry'].affine_transform(geotransform)
            if name_list['lon_max'] > 180:
                vec_frame = split_lon_max(vec_frame, geotype=MultiLineString)
            schema_ = gpd.io.file.infer_schema(vec_frame)
            # Save to GeoJSON
            vec_frame.to_file(name_list['output_path'] + 'geometry/vector_field/' + filename + '.'+drive, driver=drive, schema=schema_)
        else:
            vec_frame = gpd.GeoDataFrame(vec_frame)
            vec_frame['geometry'] = loads('LINESTRING EMPTY')
            # Save to GeoJSON
            vec_frame.to_file(name_list['output_path'] + 'geometry/vector_field/' + filename + '.'+drive, driver=drive)       
        
def to_netcdf(args):
    """
    Convert cluster features stored in a Parquet file to NetCDF format.

    This function reads cluster data from a Parquet file, processes it to create a 3D array 
    representing cluster labels across different thresholds, and saves this data to a NetCDF file.

    Parameters
    ----------
    args : tuple
        A tuple containing the following elements:
        - file : str
            Path to the input Parquet file containing cluster features.
        - name_list : dict
            Dictionary containing configuration settings:
            - 'output_path': Directory path where output NetCDF files will be saved.
            - 'x_dim': Number of x-dimensions for the output array.
            - 'y_dim': Number of y-dimensions for the output array.
            - 'thresholds': List of thresholds used for clustering.
            - 'lon_min': Minimum longitude of the spatial domain.
            - 'lon_max': Maximum longitude of the spatial domain.
            - 'lat_min': Minimum latitude of the spatial domain.
            - 'lat_max': Maximum latitude of the spatial domain.
        - comp_lvl : int
            Compression level for the NetCDF file (0-9).

    Returns
    -------
    None
    """
    file, name_list, comp_lvl = args
    # Chck if file exist and delete
    if pathlib.Path(name_list['output_path'] + 'clusters/' + pathlib.Path(file).stem + '.nc').exists():
        pathlib.Path(name_list['output_path'] + 'clusters/' + pathlib.Path(file).stem + '.nc').unlink()    
    filename = pathlib.Path(file).stem
    feature_frame = gpd.read_parquet(file)
    feature_frame = feature_frame[feature_frame['geometry'].notna()]
    
    timestamp = datetime.strptime(filename, '%Y%m%d_%H%M')
    # Create empty array based on shape of data with dimensions with len of name_list['thresholds']
    shape = (len(name_list['thresholds']), name_list['y_dim'], name_list['x_dim'])
    cluster_array = np.zeros(shape, dtype=float)
    # Fill array with the cluster labels    
    feature_frame = feature_frame.groupby('threshold_level').agg({'uid': list, 'iuid': list,'array_y': list,'array_x': list})
    for lvl, row in feature_frame.iterrows():
        if lvl == 0:
            values = row['uid']
        else:
            values = row['iuid']
        y_coords = row['array_y']
        x_coords = row['array_x']
        for cl in range(len(values)):
            cluster_array[lvl, y_coords[cl], x_coords[cl]] = values[cl]    
    # Create longitude and latitude array
    LON_MIN = name_list['lon_min']
    LON_MAX = name_list['lon_max']
    LAT_MIN = name_list['lat_min']
    LAT_MAX = name_list['lat_max']
    lon = np.linspace(LON_MIN, LON_MAX, cluster_array.shape[-1])
    lat = np.linspace(LAT_MIN, LAT_MAX, cluster_array.shape[-2])
    # Check if the longitude is between -180 and 180
    if LON_MAX > 180:
        lon_pos = np.where(lon > 180)
        lon_val = lon[lon_pos] - 360
        lon = np.delete(lon, lon_pos)
        lon = np.insert(lon, 0, lon_val)
        saved_ = cluster_array[..., lon_pos[0]]
        cluster_array = np.delete(cluster_array, lon_pos, axis=-1)
        cluster_array = np.concatenate((saved_, cluster_array), axis=-1)
    if LON_MIN < -180:
        lon_pos = np.where(lon < -180)
        lon_val = lon[lon_pos] + 360
        lon = np.delete(lon, lon_pos)
        lon = np.append(lon, lon_val)
        saved_ = cluster_array[..., lon_pos[0]]
        cluster_array = np.delete(cluster_array, lon_pos, axis=-1)
        cluster_array = np.concatenate((cluster_array, saved_), axis=-1)        
    # Create xarray
    data_xarray = xr.DataArray(cluster_array,
                            coords=[np.arange(cluster_array.shape[0]), lat, lon],
                            dims=['threshold-level', 'lat', 'lon'])
    # Add dimension time
    data_xarray = data_xarray.expand_dims({'time': [timestamp]})
    data_xarray.name = "Band1"
    data_xarray.attrs["_FillValue"] = 0
    data_xarray.attrs["units"] = "1"
    data_xarray.attrs["long_name"] = "Cluster"
    data_xarray.attrs["standard_name"] = "Cluster ID"
    data_xarray.attrs["crs"] = "EPSG:4326"
    data_xarray.attrs["description"] = "This is an output from FortraCC"
    data_xarray.to_netcdf(name_list['output_path'] + 'clusters/' + filename + '.nc', encoding={'Band1': {'zlib': True, 'complevel': comp_lvl}})


def split_lon_max(geo_df,geotype=MultiPolygon):
    """
    Adjust geometries in a GeoDataFrame to handle cases where longitude values exceed 180 degrees.

    This function processes geometries that span across the International Date Line by splitting and 
    translating them to ensure they are within valid longitude ranges. It handles geometries with 
    longitudes greater than 180 degrees and adjusts them accordingly.

    Parameters:
    ----------
    geo_df : GeoDataFrame
        A GeoDataFrame containing geometries with longitude values that may exceed 180 degrees.

    geotype : GeometryCollection, optional
        The type of geometry to use for combining split geometries. The default is `MultiPolygon`.

    Returns:
    -------
    GeoDataFrame
        A new GeoDataFrame with adjusted geometries, ensuring all longitude values are within the valid range.
    """
    ### Clip geometries in tttt larger LONGITUDE than 180
    geo_df1 = geo_df[geo_df.geometry.bounds['maxx']<=180]
    geo_df2 = geo_df[geo_df.geometry.bounds['maxx']>180]
    nones = geo_df[~geo_df.index.isin(geo_df1.index) & ~geo_df.index.isin(geo_df2.index)]
    geo_df2.geometry = geo_df2.translate(xoff=-360)
    geo_df3 = geo_df2[geo_df2.geometry.bounds['minx']<-180]
    # Create a line -90 to 90 in latitude and 180 to 180 in longitude
    line = LineString([(-180, -90), (-180, 90)])
    geo_df4 = geo_df3.geometry.apply(lambda x: split(x,line))
    # Get GeometryCollection explode and bounds['maxx'] < -180 apply translate xoff=360 and set as MultiPolygon
    geo_df5 = geo_df4.explode().apply(lambda x: translate(x, xoff=360)  if x.bounds[0]<-180 else x)
    # Merge to a single geotype
    multgeos = geo_df5.reset_index().groupby('level_0').apply(lambda x: geotype(x.geometry.values))
    if len(multgeos) > 0:
        geo_df2.loc[multgeos.index, 'geometry'] = multgeos.values
    output_df = gpd.GeoDataFrame(pd.concat([geo_df1, geo_df2]))
    output_df = gpd.GeoDataFrame(pd.concat([output_df, nones])).sort_index()
    return output_df

