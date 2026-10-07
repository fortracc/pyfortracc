import glob
import pandas as pd
import multiprocessing as mp
import xarray as xr
import numpy as np
import pathlib
from affine import Affine
from rasterio import features
from rasterio.transform import from_bounds, rowcol
from shapely.wkt import loads
from pyfortracc.utilities.utils import (set_nworkers, get_loading_bar, check_operational_system, get_geotransform,
                                        grid_coordinates)
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
    
    # Output grid = tracking grid. The cluster geometries are burned (and the opt_field points placed)
    # directly on it, so every value lands on the pixels of its cluster.
    out_shape = (name_list['y_dim'], name_list['x_dim'])
    if use_latlon:
        # Rows from north to south; coordinates are the pixel centres (the bounds are the outer edges)
        grid_transform = from_bounds(name_list['lon_min'], name_list['lat_min'],
                                     name_list['lon_max'], name_list['lat_max'],
                                     name_list['x_dim'], name_list['y_dim'])
        lons, lats = grid_coordinates(name_list)
        lons, lats = lons.astype(np.float32), lats[::-1].astype(np.float32)
        
        # Create coordinates dictionary with threshold_level
        coords = {
            'time': [timestamp],
            'threshold_level': threshold_levels,
            'lat': lats,
            'lon': lons
        }
        spatial_dims = ('time', 'threshold_level', 'lat', 'lon')
    else:
        # Pixel space of the cluster geometries without bounds: pixel (row y, col x) spans x - 0.5 .. x + 0.5
        grid_transform = Affine(1, 0, -0.5, 0, 1, -0.5)
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
                    # Pixel of the tracking grid that contains each start point
                    rows, cols = rowcol(grid_transform, [pt.x for pt in point_geoms], [pt.y for pt in point_geoms])
                    rows, cols = np.asarray(rows, dtype=int), np.asarray(cols, dtype=int)
                    inside = (rows >= 0) & (rows < out_shape[0]) & (cols >= 0) & (cols < out_shape[1])
                    u_all_levels[level_idx, rows[inside], cols[inside]] = np.asarray(opt_field_u)[inside]
                    v_all_levels[level_idx, rows[inside], cols[inside]] = np.asarray(opt_field_v)[inside]
            
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
        
        # Standard processing for all other columns (numeric only) - loop over threshold levels
        try:
            col_values = pd.to_numeric(df_original[col]).astype(np.float32)
        except (TypeError, ValueError):
            print(f"Warning: Column '{col}' is not numeric. Skipping.")
            continue
        for level_idx, threshold_level in enumerate(threshold_levels):
            # Clusters of this threshold level with a value
            rows = (df_original['threshold_level'] == threshold_level) & col_values.notna()
            if not rows.any():
                continue
            
            # Burn the cluster geometries on the tracking grid (pixels whose centre is inside a cluster)
            shapes = [(geom, value) for geom, value in zip(df_original.loc[rows, 'geometry'].apply(loads),
                                                           col_values[rows])
                      if geom is not None and not geom.is_empty]
            if shapes:
                col_all_levels[level_idx, :, :] = features.rasterize(
                    shapes, out_shape=out_shape, transform=grid_transform, fill=np.nan, dtype='float32')
        
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