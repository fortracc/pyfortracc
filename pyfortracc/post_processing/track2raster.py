import glob
import pandas as pd
import multiprocessing as mp
import geopandas as gpd
import xarray as xr
import numpy as np
import pathlib
from geocube.api.core import make_geocube
from shapely.wkt import loads
from pyfortracc.utilities.utils import set_nworkers, get_loading_bar, check_operational_system, get_geotransform
from pyfortracc.default_parameters import default_parameters


def track2raster(name_list, read_function, columns=None, parallel=False):
    """
    Convert tracking data to raster format in netCDF.
    
    Parameters:
    -----------
    name_list : dict
        Dictionary with configuration parameters
    read_function : function
        Function to read input data
    columns : list, optional
        List of column names to convert. If None, will process u_/v_ columns automatically.
        Special handling for 'opt_field' column (LineString/MultiLineString).
    parallel : bool, optional
        Whether to use parallel processing
    """
    print('Track to Raster Conversion:')
    # Check operational system
    name_list, parallel = check_operational_system(name_list, parallel)
    # Get all track files
    files = sorted(glob.glob(name_list['output_path'] + 'track/trackingtable/' + '*.parquet'))
    if len(files) == 0:
        print('No track files found at ' + name_list['output_path'] + 'track/trackingtable/')
        return
    # Set default parameters
    name_list = default_parameters(name_list, read_function)
    n_workers = set_nworkers(name_list)
    # Get reverse geotransform
    _, gtf_inv = get_geotransform(name_list)
    # Get loading bar
    loading_bar = get_loading_bar(files)
    # Check if parallel or not
    if parallel and n_workers > 1:
        # Create a pool of workers
        with mp.Pool(n_workers) as pool:
            for _ in pool.imap_unordered(process_file, [(file, name_list, gtf_inv, columns) for file in files]):
                loading_bar.update()
        pool.close()
        pool.join()
    else:
        for file in files:
            process_file((file, name_list, gtf_inv, columns))
            loading_bar.update()
    loading_bar.close()
    return

def process_file(args):
    file, name_list, gtf_inv, columns = args
    df_original = pd.read_parquet(file)
    if df_original.empty:
        return
    
    # Sort by threshold_level to ensure lower thresholds are processed first
    df_original = df_original.sort_values('threshold_level').reset_index(drop=True)
    
    # Determine which columns to process
    if columns is None:
        # Default behavior: get all u_ and v_ columns
        columns_to_process = []
        for col in df_original.columns:
            if col.startswith('u_') or col.startswith('v_'):
                columns_to_process.append(col)
    else:
        # Custom columns: verify they exist in the dataframe
        columns_to_process = []
        for col in columns:
            if col not in df_original.columns:
                print(f"Warning: Column '{col}' not found in {file}. Skipping.")
                continue
            columns_to_process.append(col)
    
    if not columns_to_process:
        return
    
    # Get timestamp
    timestamp = pd.to_datetime(df_original['timestamp'].unique()[0])
    
    # Calculate resolution and grid parameters based on lat/lon if available
    if all(key in name_list and name_list[key] is not None for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
        res_lat = abs(name_list['lat_max'] - name_list['lat_min']) / name_list['y_dim']
        res_lon = abs(name_list['lon_max'] - name_list['lon_min']) / name_list['x_dim']
        resolution = (res_lon, res_lat)
        
        # Create consistent lat/lon coordinates for all variables
        lons = np.linspace(name_list['lon_min'], name_list['lon_max'], name_list['x_dim'], dtype=np.float32)
        lats = np.linspace(name_list['lat_max'], name_list['lat_min'], name_list['y_dim'], dtype=np.float32)
        
        # Create dataset with predefined coordinates
        ds = xr.Dataset(coords={'time': [timestamp], 'lat': lats, 'lon': lons})
        ds['lat'].attrs = {'units': 'degrees_north', 'long_name': 'latitude', 'standard_name': 'latitude'}
        ds['lon'].attrs = {'units': 'degrees_east', 'long_name': 'longitude', 'standard_name': 'longitude'}
    else:
        resolution = (1, 1)
        # Create dataset without predefined spatial coordinates
        ds = xr.Dataset(coords={'time': [timestamp]})
    # Process each column
    for col in columns_to_process:
        # Special handling for opt_field (LineString/MultiLineString geometries)
        if col == 'opt_field':
            df_col = df_original[['geometry', col]].copy()
            df_col = df_col.dropna(subset=[col]).reset_index(drop=True)
            
            if df_col.empty:
                continue
            
            # Create lists to store point geometries and vectors
            from shapely.geometry import Point
            point_geoms = []
            opt_field_u = []
            opt_field_v = []
            
            # Process each row - extract start points of vectors
            for idx, row in df_col.iterrows():
                opt_geom = loads(row[col])
                
                if opt_geom.is_empty:
                    continue
                
                # Extract u/v and start point from LineString/MultiLineString
                if opt_geom.geom_type == 'MultiLineString':
                    for line in opt_geom.geoms:
                        # Use start point as the location
                        point_geoms.append(Point(line.coords[0]))
                        opt_field_u.append(line.coords[-1][0] - line.coords[0][0])
                        opt_field_v.append(line.coords[-1][1] - line.coords[0][1])
                elif opt_geom.geom_type == 'LineString':
                    point_geoms.append(Point(opt_geom.coords[0]))
                    opt_field_u.append(opt_geom.coords[-1][0] - opt_geom.coords[0][0])
                    opt_field_v.append(opt_geom.coords[-1][1] - opt_geom.coords[0][1])
            
            if len(point_geoms) > 0:
                # Create GeoDataFrame with point geometries (much faster!)
                gdf = gpd.GeoDataFrame({
                    'u_opt_field': opt_field_u,
                    'v_opt_field': opt_field_v
                }, geometry=point_geoms, crs='EPSG:4326')
                
                # Create cube
                cube = make_geocube(
                    vector_data=gdf,
                    measurements=['u_opt_field', 'v_opt_field'],
                    resolution=resolution,
                    fill=np.nan
                )
                
                # Add to dataset with correct dimensions
                if 'lat' in ds.coords and 'lon' in ds.coords:
                    # Rename cube dimensions from y,x to lat,lon and interpolate
                    cube_renamed = cube.rename({'y': 'lat', 'x': 'lon'})
                    cube_interp = cube_renamed.interp(lat=ds.lat, lon=ds.lon, method='nearest')
                    
                    # Add directly - now with matching coordinates
                    ds['u_opt_field'] = (('time', 'lat', 'lon'), cube_interp['u_opt_field'].values[np.newaxis, :, :])
                    ds['v_opt_field'] = (('time', 'lat', 'lon'), cube_interp['v_opt_field'].values[np.newaxis, :, :])
                else:
                    ds['u_opt_field'] = (('time', 'y', 'x'), cube['u_opt_field'].data[np.newaxis, :, :])
                    ds['v_opt_field'] = (('time', 'y', 'x'), cube['v_opt_field'].data[np.newaxis, :, :])
            
            continue
        
        # Standard processing for all other columns
        df_col = df_original[['geometry', col]].copy()
        df_col = df_col.dropna(subset=[col]).reset_index(drop=True)
        
        if df_col.empty:
            continue
        
        # Get geometries and create GeoDataFrame
        geometries = gpd.GeoSeries(df_col['geometry'].apply(loads))
        gdf = gpd.GeoDataFrame(df_col[[col]], geometry=geometries, crs='EPSG:4326')
        
        # Create cube with make_geocube
        cube = make_geocube(
            vector_data=gdf,
            measurements=[col],
            resolution=resolution,
            fill=np.nan
        )
        
        # Add to dataset with correct dimensions
        if 'lat' in ds.coords and 'lon' in ds.coords:
            # Rename cube dimensions from y,x to lat,lon and interpolate
            cube_renamed = cube.rename({'y': 'lat', 'x': 'lon'})
            cube_interp = cube_renamed.interp(lat=ds.lat, lon=ds.lon, method='nearest')
            
            # Add directly - now with matching coordinates
            ds[col] = (('time', 'lat', 'lon'), cube_interp[col].values[np.newaxis, :, :])
        else:
            ds[col] = (('time', 'y', 'x'), cube[col].data[np.newaxis, :, :])
    
    # Check if dataset has any variables
    if len(ds.data_vars) == 0:
        return
    
    # Add variable attributes if we have lat/lon coordinates
    if 'lat' in ds.coords and 'lon' in ds.coords:
        for var in ds.data_vars:
            ds[var].attrs['crs'] = 'EPSG:4326'
            ds[var].attrs['_FillValue'] = np.nan
    
    # Save dataset to netCDF file
    output_file = file.replace('trackingtable', 'raster').replace('.parquet', '.nc')
    output_path = pathlib.Path(output_file).parent
    output_path.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(output_file)
    
    return