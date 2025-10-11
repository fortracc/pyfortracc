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
    u_cols = []
    v_cols = []
    for col in df_original.columns:
        if col.startswith('u_'):
            u_cols.append(col)
        elif col.startswith('v_'):
            v_cols.append(col)
    
    # Get timestamp
    timestamp = pd.to_datetime(df_original['timestamp'].unique()[0])
    
    # Create an xarray dataset to store all vectors based on methods
    ds = xr.Dataset()
    ds = ds.assign_coords(time=('time', [timestamp]))
    
    # Check if there's any valid data
    has_valid_data = False
    for u_col, v_col in zip(u_cols, v_cols):
        if not df_original[[u_col, v_col]].isna().all().all():
            has_valid_data = True
            break
    
    if not has_valid_data:
        # Save empty dataset to netCDF file
        output_file = file.replace('trackingtable', 'spatial_vectors').replace('.parquet', '.nc')
        output_path = pathlib.Path(output_file).parent
        output_path.mkdir(parents=True, exist_ok=True)
        ds.to_netcdf(output_file)
        return
    
    # Loop over pairs of u and v columns
    for u_col, v_col in zip(u_cols, v_cols):
        # Extract method name from column name
        method = u_col[2:]
        
        # Create a copy for this method
        if method == 'opt' and 'opt_field' in df_original.columns:
            df_method = df_original[['geometry', u_col, v_col, 'opt_field', 'threshold_level']].copy()
            df_method = df_method.dropna(subset=[u_col, v_col, 'opt_field'], how='any').reset_index(drop=True)
        else:
            df_method = df_original[['geometry', u_col, v_col, 'threshold_level']].copy()
            df_method = df_method.dropna(subset=[u_col, v_col], how='any').reset_index(drop=True)
         
        if df_method.empty:
            continue
        
        # Get geometries for this specific method (after filtering)
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
        
        # Check if name_list have lat_min, lat_max, lon_min, lon_max is different from None
        if all(key in name_list and name_list[key] is not None for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
            # Apply reverse geotransform using geopandas affine_transform
            geometries_gdf = gpd.GeoDataFrame(geometry=geometries, crs='EPSG:4326')
            geometries = geometries_gdf['geometry'].affine_transform(gtf_inv)
            
            # Transform opt_field coordinates if they exist
            if opt_field_x:
                opt_field_coords = gpd.GeoSeries([gpd.points_from_xy([x], [y])[0] for x, y in zip(opt_field_x, opt_field_y)], crs='EPSG:4326')
                opt_field_coords_transformed = opt_field_coords.affine_transform(gtf_inv)
                opt_field_x = [geom.x for geom in opt_field_coords_transformed]
                opt_field_y = [geom.y for geom in opt_field_coords_transformed]

        # Create GeoDataFrame with filtered data and corresponding geometries
        gdf = gpd.GeoDataFrame(df_method[[u_col, v_col]], geometry=geometries.values)
        # Set CRS using EPSG:3857 (metric)
        gdf.set_crs(epsg=3857, inplace=True, allow_override=True)
        
        # GeoCube - create cube with ALL data (already sorted by threshold_level)
        cube = make_geocube(
            vector_data=gdf,
            measurements=[u_col, v_col],
            resolution=(1, 1),
            fill=np.nan
        )

        # --- Extract only points with values ---
        u_cube = cube[u_col].data  # array 2D [y, x]
        v_cube = cube[v_col].data  # array 2D [y, x]
        x_coords = cube.coords['x'].data
        y_coords = cube.coords['y'].data 
        
        # Create meshgrid of x and y coordinates
        X, Y = np.meshgrid(x_coords, y_coords)
        mask = ~np.isnan(u_cube) & ~np.isnan(v_cube)
        
        # Get valid points from cube
        x_list = X[mask].astype(float).tolist()
        y_list = Y[mask].astype(float).tolist()
        u_list = u_cube[mask].astype(float).tolist()
        v_list = v_cube[mask].astype(float).tolist()
        
        # Add opt_field values (already calculated before transformation)
        if method == 'opt' and opt_field_x:
            x_list.extend(opt_field_x)
            y_list.extend(opt_field_y)
            u_list.extend(opt_field_u)
            v_list.extend(opt_field_v)
        
        # Create matrices filled with NaN
        u_matrix = np.full((name_list['y_dim'], name_list['x_dim']), np.nan, dtype=np.float32)
        v_matrix = np.full((name_list['y_dim'], name_list['x_dim']), np.nan, dtype=np.float32)
            
        if len(x_list) > 0:
            # Convert all x and y to int and fit to bounds of x_dim and y_dim
            x_arr = np.array(x_list, dtype=np.int32)
            y_arr = np.array(y_list, dtype=np.int32)
            x_arr = np.clip(x_arr, 0, name_list['x_dim'] - 1)
            y_arr = np.clip(y_arr, 0, name_list['y_dim'] - 1)
            u_arr = np.array(u_list, dtype=np.float32)
            v_arr = np.array(v_list, dtype=np.float32)
            
            # Fill matrix - values are already in order (lower to higher threshold)
            u_matrix[y_arr, x_arr] = u_arr
            v_matrix[y_arr, x_arr] = v_arr
        
        # Add to dataset
        ds['u_' + method] = (('time', 'y', 'x'), u_matrix[np.newaxis, :, :])
        ds['v_' + method] = (('time', 'y', 'x'), v_matrix[np.newaxis, :, :])
        
        # Remove variables to free memory
        del gdf, cube, geometries, df_method, u_cube, v_cube, X, Y, mask
        del x_list, y_list, u_list, v_list, u_matrix, v_matrix
    
    # Check if have lat and lon in name_list and add dimensions
    if all(key in name_list and name_list[key] is not None for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
        # Criar arrays de latitude e longitude
        lats = np.linspace(name_list['lat_min'], name_list['lat_max'], name_list['y_dim'], dtype=np.float32)
        lons = np.linspace(name_list['lon_min'], name_list['lon_max'], name_list['x_dim'], dtype=np.float32)
        
        # Renomear dimensões de y,x para lat,lon
        ds = ds.rename({'y': 'lat', 'x': 'lon'})
        
        # Atribuir coordenadas
        ds = ds.assign_coords(lat=('lat', lats))
        ds = ds.assign_coords(lon=('lon', lons))
        
        # Adicionar atributos às coordenadas
        ds['lat'].attrs['units'] = 'degrees_north'
        ds['lat'].attrs['long_name'] = 'latitude'
        ds['lat'].attrs['standard_name'] = 'latitude'
        
        ds['lon'].attrs['units'] = 'degrees_east'
        ds['lon'].attrs['long_name'] = 'longitude'
        ds['lon'].attrs['standard_name'] = 'longitude'
        
        # Adicionar atributos às variáveis de dados
        for var in ds.data_vars:
            ds[var].attrs['crs'] = 'EPSG:4326'
            ds[var].attrs['_FillValue'] = np.nan
    else:
        ds = ds.assign_coords(y=('y', np.arange(name_list['y_dim'], dtype=np.int32)))
        ds = ds.assign_coords(x=('x', np.arange(name_list['x_dim'], dtype=np.int32)))

    # Save dataset to netCDF file
    output_file = file.replace('trackingtable', 'spatial_vectors').replace('.parquet', '.nc')
    output_path = pathlib.Path(output_file).parent
    output_path.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(output_file)
    
    # Clean up
    del df_original, ds
    return