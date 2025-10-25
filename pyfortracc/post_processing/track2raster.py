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
    
    # Get unique threshold levels (already sorted) - ensure it's a numpy array
    threshold_levels = np.array(sorted(df_original['threshold_level'].unique()))
    n_levels = len(threshold_levels)
    
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
    
    # Check if using lat/lon coordinates
    use_latlon = all(key in name_list and name_list[key] is not None 
                     for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max'])
    
    # Calculate resolution and grid parameters based on lat/lon if available
    if use_latlon:
        res_lat = abs(name_list['lat_max'] - name_list['lat_min']) / name_list['y_dim']
        res_lon = abs(name_list['lon_max'] - name_list['lon_min']) / name_list['x_dim']
        resolution = (res_lon, res_lat)
        
        # Create consistent lat/lon coordinates for all variables
        lons = np.linspace(name_list['lon_min'], name_list['lon_max'], name_list['x_dim'], dtype=np.float32)
        lats = np.linspace(name_list['lat_max'], name_list['lat_min'], name_list['y_dim'], dtype=np.float32)
        
        # Create coordinates dictionary with threshold_level
        coords = {
            'time': [timestamp],
            'threshold_level': threshold_levels,
            'lat': lats,
            'lon': lons
        }
        spatial_dims = ('time', 'threshold_level', 'lat', 'lon')
    else:
        resolution = (1, 1)
        # Create coordinates dictionary without lat/lon but with threshold_level
        coords = {
            'time': [timestamp],
            'threshold_level': threshold_levels,
            'y': np.arange(name_list['y_dim'], dtype=np.int32),
            'x': np.arange(name_list['x_dim'], dtype=np.int32)
        }
        spatial_dims = ('time', 'threshold_level', 'y', 'x')
    
    # Dictionary to store all data variables
    data_vars = {}
    # Process each column
    for col in columns_to_process:
        # Create arrays to store data for all threshold levels
        # Dimensions: (threshold_level, y, x) or (threshold_level, lat, lon)
        col_all_levels = np.full((n_levels, name_list['y_dim'], name_list['x_dim']), np.nan, dtype=np.float32)
        
        # Special handling for columns ending in '_values' with corresponding '_xy' positions
        if col.endswith('_values'):
            # Check if corresponding _xy column exists
            col_base = col.replace('_values', '')  # Remove '_values' suffix
            col_xy = f"{col_base}_xy"
            
            if col_xy in df_original.columns:
                # Direct insertion using pre-computed positions
                # _xy contains pixel indices [col, row] in the tracking grid
                
                # Process each threshold level
                for level_idx, threshold_level in enumerate(threshold_levels):
                    # Filter data for this specific threshold level
                    df_level = df_original[df_original['threshold_level'] == threshold_level].copy()
                    
                    # Check if columns exist in this filtered dataframe
                    if col not in df_level.columns or col_xy not in df_level.columns:
                        continue
                    
                    # Process each row
                    for idx, row in df_level.iterrows():
                        values = row[col]
                        positions = row[col_xy]
                        
                        # Skip if values or positions are NaN, None, or empty
                        if values is None or positions is None:
                            continue
                        if isinstance(values, float) and np.isnan(values):
                            continue
                        if isinstance(positions, float) and np.isnan(positions):
                            continue
                        if not isinstance(values, (list, np.ndarray)) or not isinstance(positions, (list, np.ndarray)):
                            continue
                        if len(values) == 0 or len(positions) == 0:
                            continue
                        
                        # Ensure both lists have same length
                        if len(values) != len(positions):
                            continue
                        
                        # Insert values at corresponding positions
                        # positions are in format [col, row] (x, y) as pixel indices
                        for val, pos in zip(values, positions):
                            if not isinstance(pos, (list, np.ndarray)) or len(pos) < 2:
                                continue
                            
                            try:
                                x_pos, y_pos = int(pos[0]), int(pos[1])
                                
                                # Check if position is within bounds
                                if 0 <= y_pos < name_list['y_dim'] and 0 <= x_pos < name_list['x_dim']:
                                    col_all_levels[level_idx, y_pos, x_pos] = val
                            except (ValueError, TypeError, IndexError):
                                # Skip invalid positions
                                continue
                
                # Add to data_vars with DataArray
                data_vars[col_base] = xr.DataArray(
                    col_all_levels[np.newaxis, :, :, :],
                    dims=spatial_dims,
                    coords=coords
                )
                
                # Skip the rest of the processing for this column
                continue
        
        # Special handling for opt_field (LineString/MultiLineString geometries)
        if col == 'opt_field':
            # Need to process u and v components separately for each threshold level
            u_all_levels = np.full((n_levels, name_list['y_dim'], name_list['x_dim']), np.nan, dtype=np.float32)
            v_all_levels = np.full((n_levels, name_list['y_dim'], name_list['x_dim']), np.nan, dtype=np.float32)
            
            # Loop over each threshold level
            for level_idx, threshold_level in enumerate(threshold_levels):
                # Filter data for this specific threshold level
                df_level = df_original[df_original['threshold_level'] == threshold_level]
                df_col = df_level[['geometry', col]].copy()
                df_col = df_col.dropna(subset=[col])
                
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
                            point_geoms.append(Point(line.coords[0]))
                            opt_field_u.append(line.coords[-1][0] - line.coords[0][0])
                            opt_field_v.append(line.coords[-1][1] - line.coords[0][1])
                    elif opt_geom.geom_type == 'LineString':
                        point_geoms.append(Point(opt_geom.coords[0]))
                        opt_field_u.append(opt_geom.coords[-1][0] - opt_geom.coords[0][0])
                        opt_field_v.append(opt_geom.coords[-1][1] - opt_geom.coords[0][1])
                
                if len(point_geoms) > 0:
                    # Create GeoDataFrame with point geometries
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
                    
                    # Extract data and interpolate to target grid
                    if use_latlon:
                        # Rename and interpolate
                        lats_target = coords['lat']
                        lons_target = coords['lon']
                        cube_renamed = cube.rename({'y': 'lat', 'x': 'lon'})
                        cube_interp = cube_renamed.interp(lat=lats_target, lon=lons_target, method='nearest')
                        
                        u_all_levels[level_idx, :, :] = cube_interp['u_opt_field'].values
                        v_all_levels[level_idx, :, :] = cube_interp['v_opt_field'].values
                    else:
                        # Direct indexing for pixel coordinates
                        u_data = cube['u_opt_field'].data
                        v_data = cube['v_opt_field'].data
                        # Clip to target dimensions
                        y_size = min(u_data.shape[0], name_list['y_dim'])
                        x_size = min(u_data.shape[1], name_list['x_dim'])
                        u_all_levels[level_idx, :y_size, :x_size] = u_data[:y_size, :x_size]
                        v_all_levels[level_idx, :y_size, :x_size] = v_data[:y_size, :x_size]
            
            # Add to data_vars with DataArrays
            data_vars['u_opt_field'] = xr.DataArray(
                u_all_levels[np.newaxis, :, :, :],
                dims=spatial_dims,
                coords=coords
            )
            data_vars['v_opt_field'] = xr.DataArray(
                v_all_levels[np.newaxis, :, :, :],
                dims=spatial_dims,
                coords=coords
            )
            
            continue
        
        # Standard processing for all other columns - loop over threshold levels
        for level_idx, threshold_level in enumerate(threshold_levels):
            # Filter data for this specific threshold level
            df_level = df_original[df_original['threshold_level'] == threshold_level]
            df_col = df_level[['geometry', col]].copy()
            df_col = df_col.dropna(subset=[col])
            
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
            
            # Extract data and interpolate to target grid
            if use_latlon:
                # Rename and interpolate
                lats_target = coords['lat']
                lons_target = coords['lon']
                cube_renamed = cube.rename({'y': 'lat', 'x': 'lon'})
                cube_interp = cube_renamed.interp(lat=lats_target, lon=lons_target, method='nearest')
                
                col_all_levels[level_idx, :, :] = cube_interp[col].values
            else:
                # Direct indexing for pixel coordinates
                col_data = cube[col].data
                # Clip to target dimensions
                y_size = min(col_data.shape[0], name_list['y_dim'])
                x_size = min(col_data.shape[1], name_list['x_dim'])
                col_all_levels[level_idx, :y_size, :x_size] = col_data[:y_size, :x_size]
        
        # Add to data_vars with DataArray
        data_vars[col] = xr.DataArray(
            col_all_levels[np.newaxis, :, :, :],
            dims=spatial_dims,
            coords=coords
        )
    
    # Check if there are any variables to save
    if len(data_vars) == 0:
        return
    
    # Create the xarray Dataset from DataArrays
    ds = xr.Dataset(data_vars)
    
    # Add attributes to coordinates
    ds['time'].attrs['long_name'] = 'Time'
    ds['time'].attrs['standard_name'] = 'time'
    
    ds['threshold_level'].attrs['long_name'] = 'Threshold Level'
    ds['threshold_level'].attrs['description'] = 'Intensity threshold level used for tracking'
    
    # Add variable attributes if we have lat/lon coordinates
    if use_latlon:
        ds['lat'].attrs['units'] = 'degrees_north'
        ds['lat'].attrs['long_name'] = 'latitude'
        ds['lat'].attrs['standard_name'] = 'latitude'
        
        ds['lon'].attrs['units'] = 'degrees_east'
        ds['lon'].attrs['long_name'] = 'longitude'
        ds['lon'].attrs['standard_name'] = 'longitude'
        
        for var in ds.data_vars:
            ds[var].attrs['crs'] = 'EPSG:4326'
            ds[var].attrs['_FillValue'] = np.nan
    else:
        ds['y'].attrs['long_name'] = 'y coordinate'
        ds['x'].attrs['long_name'] = 'x coordinate'
    
    # Save dataset to netCDF file
    output_file = file.replace('trackingtable', 'raster').replace('.parquet', '.nc')
    output_path = pathlib.Path(output_file).parent
    output_path.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(output_file)
    
    return