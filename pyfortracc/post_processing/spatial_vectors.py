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


def spatial_vectors(name_list, read_function, parallel=False):

    print('Spatial Vectors Conversion:')
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
            for _ in pool.imap_unordered(process_file, [(file, name_list, gtf_inv) for file in files]):
                loading_bar.update()
        pool.close()
        pool.join()
    else:
        for file in files:
            process_file((file, name_list, gtf_inv))
            loading_bar.update()
    loading_bar.close()
    return

def process_file(args):
    file, name_list, gtf_inv = args
    df_original = pd.read_parquet(file)
    if df_original.empty:
        return
    
    # Sort by threshold_level to ensure lower thresholds are processed first
    df_original = df_original.sort_values('threshold_level').reset_index(drop=True)
    
    # Get vectors of all methods based on columns where contains u_ and v_
    u_cols = [col for col in df_original.columns if col.startswith('u_')]
    v_cols = [col for col in df_original.columns if col.startswith('v_')]
    
    # Get timestamp
    timestamp = pd.to_datetime(df_original['timestamp'].unique()[0])
    
    # Get unique threshold levels (already sorted) - ensure it's a numpy array
    threshold_levels = np.array(sorted(df_original['threshold_level'].unique()))
    n_levels = len(threshold_levels)
    
    # Check if there's any valid data
    has_valid_data = any(not df_original[[u_col, v_col]].isna().all().all() 
                         for u_col, v_col in zip(u_cols, v_cols))
    
    if not has_valid_data:
        return
    
    # Pre-create spatial dimensions and coordinates
    use_latlon = all(key in name_list and name_list[key] is not None 
                     for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max'])
    
    if use_latlon:
        lats = np.linspace(name_list['lat_min'], name_list['lat_max'], name_list['y_dim'], dtype=np.float32)
        lons = np.linspace(name_list['lon_min'], name_list['lon_max'], name_list['x_dim'], dtype=np.float32)
        coords = {
            'time': [timestamp],
            'threshold_level': threshold_levels,
            'lat': lats,
            'lon': lons
        }
        spatial_dims = ('time', 'threshold_level', 'lat', 'lon')
    else:
        coords = {
            'time': [timestamp],
            'threshold_level': threshold_levels,
            'y': np.arange(name_list['y_dim'], dtype=np.int32),
            'x': np.arange(name_list['x_dim'], dtype=np.int32)
        }
        spatial_dims = ('time', 'threshold_level', 'y', 'x')
    
    # Dictionary to store all data variables
    data_vars = {}
    
    # Loop over pairs of u and v columns
    for u_col, v_col in zip(u_cols, v_cols):
        # Extract method name from column name
        method = u_col[2:]
        
        # Create 3D arrays to store vectors for all threshold levels
        # Dimensions: (threshold_level, y, x)
        u_all_levels = np.full((n_levels, name_list['y_dim'], name_list['x_dim']), np.nan, dtype=np.float32)
        v_all_levels = np.full((n_levels, name_list['y_dim'], name_list['x_dim']), np.nan, dtype=np.float32)
        
        # Loop over each threshold level
        for level_idx, threshold_level in enumerate(threshold_levels):
            # Filter data for this specific threshold level and method
            mask_level = df_original['threshold_level'] == threshold_level
            df_level = df_original[mask_level]
            
            # Select columns and drop NaN
            if method == 'opt' and 'opt_field' in df_level.columns:
                cols = ['geometry', u_col, v_col, 'opt_field']
                df_method = df_level[cols].dropna(subset=[u_col, v_col, 'opt_field'])
            else:
                cols = ['geometry', u_col, v_col]
                df_method = df_level[cols].dropna(subset=[u_col, v_col])
             
            if df_method.empty:
                continue
            
            # Get geometries for this specific method and level
            geometries = gpd.GeoSeries(df_method['geometry'].apply(loads))
            
            # Process opt_field BEFORE transformation to get correct u/v components
            opt_field_u = []
            opt_field_v = []
            opt_field_x = []
            opt_field_y = []
            
            if method == 'opt' and 'opt_field' in df_method.columns:
                opt_field_series = df_method['opt_field'].dropna().reset_index(drop=True)
                if not opt_field_series.empty:
                    opt_field_geom = gpd.GeoSeries(opt_field_series.apply(loads))
                    opt_field_geom = opt_field_geom[~opt_field_geom.is_empty]
                    
                    if not opt_field_geom.empty:
                        # Calculate u/v BEFORE transformation (in original coordinate system)
                        for geom in opt_field_geom:
                            if geom.geom_type == 'MultiLineString':
                                for line in geom.geoms:
                                    opt_field_x.append(line.coords[0][0])
                                    opt_field_y.append(line.coords[0][1])
                                    opt_field_u.append(line.coords[-1][0] - line.coords[0][0])
                                    opt_field_v.append(line.coords[-1][1] - line.coords[0][1])
                            elif geom.geom_type == 'LineString':
                                opt_field_x.append(geom.coords[0][0])
                                opt_field_y.append(geom.coords[0][1])
                                opt_field_u.append(geom.coords[-1][0] - geom.coords[0][0])
                                opt_field_v.append(geom.coords[-1][1] - geom.coords[0][1])
            
            # Apply reverse geotransform if coordinates are provided
            if use_latlon:
                geometries = gpd.GeoDataFrame(geometry=geometries, crs='EPSG:4326')['geometry'].affine_transform(gtf_inv)
                
                # Transform opt_field coordinates if they exist
                if opt_field_x:
                    opt_field_coords = gpd.GeoSeries.from_xy(opt_field_x, opt_field_y, crs='EPSG:4326')
                    opt_field_coords = opt_field_coords.affine_transform(gtf_inv)
                    opt_field_x = opt_field_coords.x.tolist()
                    opt_field_y = opt_field_coords.y.tolist()
                
                # Create GeoDataFrame with filtered data (with CRS for lat/lon)
                gdf = gpd.GeoDataFrame(df_method[[u_col, v_col]], geometry=geometries.values)
                gdf.set_crs(epsg=3857, inplace=True, allow_override=True)
            else:
                # For pixel coordinates (no lat/lon), geometries are already in pixel space
                # No transformation needed - geometries are already in correct coordinate system
                gdf = gpd.GeoDataFrame(df_method[[u_col, v_col]], geometry=geometries.values)
            
            if use_latlon:
                # Use GeoCube for geographic coordinates
                cube = make_geocube(
                    vector_data=gdf,
                    measurements=[u_col, v_col],
                    resolution=(1, 1),
                    fill=np.nan
                )

                # Extract only points with values
                u_cube = cube[u_col].data
                v_cube = cube[v_col].data
                
                # Create meshgrid of coordinates
                X, Y = np.meshgrid(cube.coords['x'].data, cube.coords['y'].data)
                mask = ~(np.isnan(u_cube) | np.isnan(v_cube))
                
                # Get valid points from cube (keep as numpy arrays)
                x_list = X[mask].astype(np.float64)
                y_list = Y[mask].astype(np.float64)
                u_list = u_cube[mask].astype(np.float32)
                v_list = v_cube[mask].astype(np.float32)
                
                # Clean up
                del u_cube, v_cube, X, Y, mask
            else:
                # For pixel coordinates, extract centroids directly from geometries
                x_list = []
                y_list = []
                u_list = []
                v_list = []
                
                for idx, row in gdf.iterrows():
                    geom = row['geometry']
                    # Get centroid of geometry
                    centroid = geom.centroid
                    x_list.append(centroid.x)
                    y_list.append(centroid.y)
                    u_list.append(row[u_col])
                    v_list.append(row[v_col])
                
                # Convert to numpy arrays
                x_list = np.array(x_list, dtype=np.float64)
                y_list = np.array(y_list, dtype=np.float64)
                u_list = np.array(u_list, dtype=np.float32)
                v_list = np.array(v_list, dtype=np.float32)
            
            # Add opt_field values if available
            if method == 'opt' and opt_field_x:
                x_list = np.concatenate([x_list, np.array(opt_field_x, dtype=np.float64)])
                y_list = np.concatenate([y_list, np.array(opt_field_y, dtype=np.float64)])
                u_list = np.concatenate([u_list, np.array(opt_field_u, dtype=np.float32)])
                v_list = np.concatenate([v_list, np.array(opt_field_v, dtype=np.float32)])
            
            # Convert coordinates to integer indices and clip to bounds
            if len(x_list) > 0:
                x_idx = np.clip(x_list.astype(np.int32), 0, name_list['x_dim'] - 1)
                y_idx = np.clip(y_list.astype(np.int32), 0, name_list['y_dim'] - 1)
                
                # Fill matrices for this threshold level
                u_all_levels[level_idx, y_idx, x_idx] = u_list
                v_all_levels[level_idx, y_idx, x_idx] = v_list
            
            # Clean up
            if use_latlon:
                del gdf, cube, geometries
            else:
                del gdf, geometries
        
        # Add time dimension
        u_data = u_all_levels[np.newaxis, :, :, :]  # shape: (1, n_levels, y_dim, x_dim)
        v_data = v_all_levels[np.newaxis, :, :, :]  # shape: (1, n_levels, y_dim, x_dim)
        
        # Create DataArrays with explicit dimensions and coordinates
        data_vars['u_' + method] = xr.DataArray(
            u_data,
            dims=spatial_dims,
            coords=coords
        )
        data_vars['v_' + method] = xr.DataArray(
            v_data,
            dims=spatial_dims,
            coords=coords
        )
        
        # Remove variables to free memory
        del u_all_levels, v_all_levels, u_data, v_data
    
    # Create the xarray Dataset from DataArrays
    ds = xr.Dataset(data_vars)
    
    # Add attributes to coordinates
    ds['time'].attrs['long_name'] = 'Time'
    ds['time'].attrs['standard_name'] = 'time'
    
    ds['threshold_level'].attrs['long_name'] = 'Threshold Level'
    ds['threshold_level'].attrs['description'] = 'Intensity threshold level used for tracking'
    
    if use_latlon:
        ds['lat'].attrs['units'] = 'degrees_north'
        ds['lat'].attrs['long_name'] = 'latitude'
        ds['lat'].attrs['standard_name'] = 'latitude'
        
        ds['lon'].attrs['units'] = 'degrees_east'
        ds['lon'].attrs['long_name'] = 'longitude'
        ds['lon'].attrs['standard_name'] = 'longitude'
        
        # Add attributes to data variables
        for var in ds.data_vars:
            ds[var].attrs['crs'] = 'EPSG:4326'
            ds[var].attrs['_FillValue'] = np.nan
    else:
        ds['y'].attrs['long_name'] = 'y coordinate'
        ds['x'].attrs['long_name'] = 'x coordinate'

    # Save dataset to netCDF file
    output_file = file.replace('trackingtable', 'spatial_vectors').replace('.parquet', '.nc')
    output_path = pathlib.Path(output_file).parent
    output_path.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(output_file)
    
    # Clean up
    del df_original, ds
    return