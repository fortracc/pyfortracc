import os
import glob
import pandas as pd
import geopandas as gpd
import numpy as np
import multiprocessing as mp
from scipy import stats as scipy_stats
from rasterstats import zonal_stats
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling
from pyfortracc.utilities.utils import set_nworkers, get_loading_bar, check_operational_system

def add_raster_data(
    name_list,
    raster_function=None,
    raster_path=None,
    raster_file_pattern=None,
    merge_mode="nearest",
    time_tolerance=None,
    statistics=None,
    return_positions=False,
    parallel=True
):
    """
    Add raster data to track files using various temporal matching strategies.

    Parameters
    ----------
    name_list : dict
        A dictionary containing configuration parameters (from pyForTraCC).
    raster_path : str
        Path to raster data folder or files.
    raster_file_pattern : str
        Datetime pattern in raster filenames (e.g. '%Y.tif', '%Y%m%d_%H%M.nc').
    merge_mode : str, default='nearest'
        Defines how to match rasters to tracks. Options:
            - 'nearest'  : Select raster closest in time to each track timestamp.
            - 'fixed'    : Use the same raster for all tracks (first or latest).
            - 'tolerance': Match rasters only if within `time_tolerance`.
    time_tolerance : str or pd.Timedelta, optional
        Maximum allowed time difference (e.g. '3H', '1D') for tolerance mode.
    statistics : list or str, default=None
        Which statistics to extract from raster. Options:
            - None or 'pixels': Extract all pixel values as a list (default).
            - 'values': Extract all pixel values as a list (same as 'pixels').
            - 'mean': Extract mean value.
            - 'median': Extract median value.
            - 'std': Extract standard deviation.
            - 'min': Extract minimum value.
            - 'max': Extract maximum value.
            - 'mode': Extract mode (most frequent value).
            - 'count': Extract count of pixels.
            - 'percentile_X': Extract X-th percentile (e.g., 'percentile_25', 'percentile_75').
            - list: e.g., ['values', 'mean', 'std', 'mode', 'percentile_25', 'percentile_75'].
    return_positions : bool, default=False
        If True and statistics='values', also returns pixel positions. Two additional columns
        will be created: {var_name}_xy (pixel indices) and {var_name}_coords (spatial coordinates).
        Only applies when 'values' statistic is requested.
    parallel : bool, default=True
        Whether to enable parallel processing.
    """


    print("Adding raster data...")

    # --- Operational system checks ---
    name_list, parallel = check_operational_system(name_list, parallel)

    # --- Load track files ---
    track_dir = os.path.join(name_list["output_path"], "track", "trackingtable")
    track_files = sorted(glob.glob(os.path.join(track_dir, "*.parquet")))
    if not track_files:
        print(f"No track files found in {track_dir}")
        return

    track_timestamps = [
        pd.to_datetime(os.path.basename(f).split(".")[0], format="%Y%m%d_%H%M%S")
        for f in track_files
    ]
    track_df = pd.DataFrame({"path": track_files}, index=track_timestamps)

    # --- Load raster files ---
    raster_path = raster_path.strip()
    if os.path.splitext(raster_path)[1]:
        search_pattern = raster_path
    else:
        search_pattern = os.path.join(raster_path, "*")

    raster_files = sorted(glob.glob(search_pattern, recursive=True))
    if not raster_files:
        print(f"No raster files found in {raster_path}")
        return

    raster_timestamps = [
        pd.to_datetime(os.path.basename(f), format=raster_file_pattern)
        for f in raster_files
    ]
    raster_df = pd.DataFrame({"path": raster_files}, index=raster_timestamps)

    # --- Merge logic depending on mode ---
    if merge_mode == "nearest":
        merged_df = pd.merge_asof(
            track_df.sort_index(),
            raster_df.sort_index(),
            left_index=True,
            right_index=True,
            direction="nearest"
        )

    elif merge_mode == "fixed":
        # Use the same raster for all track files
        fixed_raster = raster_df.iloc[0]  # or use [-1] for latest
        merged_df = track_df.copy()
        merged_df["raster_path"] = fixed_raster.path

    elif merge_mode == "tolerance":
        if time_tolerance is None:
            raise ValueError("You must specify `time_tolerance` for tolerance mode.")
        tolerance = pd.Timedelta(time_tolerance)
        merged_df = pd.merge_asof(
            track_df.sort_index(),
            raster_df.sort_index(),
            left_index=True,
            right_index=True,
            direction="nearest",
            tolerance=tolerance
        )
        merged_df = merged_df.dropna(subset=["path_y"]).rename(columns={"path_y": "raster_path"})

    else:
        raise ValueError("merge_mode must be one of: 'nearest', 'fixed', or 'tolerance'")

    # open first track file to get geometry
    sample_raster = raster_df.iloc[0].path
    # Check if raster contains coordinates variables lon and lat
    if raster_function is None:
        raise ValueError("You must provide a `raster_function` to read raster data.")
    sample_data = raster_function(sample_raster)
    if not all(dim in sample_data.dims for dim in ['lon', 'lat']):
        raise ValueError("Raster data must contain 'lon' and 'lat' dimensions.")
    # Check if raster contains crs information
    if not hasattr(sample_data, 'rio') or sample_data.rio.crs is None:
        raise ValueError("Raster data must contain CRS information.")
    
    # Check for 2D variables
    if hasattr(sample_data, 'data_vars'):
        # É um Dataset
        var_2d = [var for var in sample_data.data_vars 
                  if set(sample_data[var].dims) == {'lat', 'lon'}]
    else:
        # Is a DataArray, use the name of the DataArray
        if set(sample_data.dims) == {'lat', 'lon'}:
            var_2d = [sample_data.name if sample_data.name else 'raster_data']
        else:
            var_2d = []
    if not var_2d:
        print("No 2D variables found in raster data.")
        return
    
    # --- Process files ---
    n_workers = set_nworkers(name_list)
    # Loading bar
    loading_bar = get_loading_bar(track_files)

    # Transform merged_df to tuples for easier processing
    merged_list = merged_df[['path_x', 'path_y']].itertuples(index=False, name=None)
    args_list = [(row[0], row[1], var_2d, raster_function, statistics, return_positions, name_list) for row in merged_list]

    # Execução paralela
    if parallel and n_workers > 1:
        with mp.Pool(n_workers) as pool:
            for _ in pool.imap_unordered(process_file, args_list):
                loading_bar.update()
        loading_bar.close()
    else:
        for args in args_list:
            process_file(args)
            loading_bar.update()
        loading_bar.close()


def process_file(args):
    """
    Function executed for each line of track and raster file pair.
    """

    track_file, raster_file, var_2d, raster_function, statistics, return_positions, name_list = args

    # Load track data
    track_data = gpd.GeoDataFrame(
        pd.read_parquet(track_file),
        geometry=gpd.GeoSeries.from_wkt(pd.read_parquet(track_file)['geometry']),
        crs="EPSG:4326"
    )

    # Load raster data
    raster_data = raster_function(raster_file)

    # Normalize statistics parameter
    if statistics is None or statistics == 'pixels':
        stats_to_extract = None  # Extract all pixel values
    elif isinstance(statistics, str):
        stats_to_extract = [statistics]
    else:
        stats_to_extract = statistics

    # Process each 2D variable
    for var_name in var_2d:
        # If it's a DataArray, access directly; if it's a Dataset, use the variable name
        if hasattr(raster_data, 'data_vars'):
            # It's a Dataset
            var_data = raster_data[var_name]
        else:
            # It's a DataArray
            var_data = raster_data
        
        # Ensure proper dimension order (lat, lon)
        if 'lat' in var_data.dims and 'lon' in var_data.dims:
            var_data = var_data.transpose('lat', 'lon', ...)
        
        # Get raster array
        raster_array = var_data.values
    
        # Check if array has valid dimensions
        if raster_array.ndim < 2 or min(raster_array.shape[:2]) == 0:
            raise ValueError(f"Invalid raster dimensions: {raster_array.shape}. Must be at least 2D with both dimensions > 0")
        
        # Compute zonal statistics
        # Always calculate affine transform from coordinates for reliability
        if 'lon' in var_data.coords and 'lat' in var_data.coords:
            lon = var_data.coords['lon'].values
            lat = var_data.coords['lat'].values
            
            # Ensure we have valid coordinate arrays
            if len(lon) == 0 or len(lat) == 0:
                raise ValueError(f"Invalid coordinate dimensions: lon={len(lon)}, lat={len(lat)}")
            
            # Calculate pixel size
            # Note: from_bounds expects (west, south, east, north, width, height)
            # width corresponds to number of columns (longitude dimension)
            # height corresponds to number of rows (latitude dimension)
            # The array shape should be (height, width) = (lat, lon)
            height, width = raster_array.shape[:2]
            affine_transform = from_bounds(
                lon.min(), lat.min(), lon.max(), lat.max(),
                width=width, height=height
            )
        else:
            raise ValueError("Cannot determine affine transform from raster data")
        
        # Get nodata value from rio if available, otherwise None
        nodata_value = var_data.rio.nodata if (hasattr(var_data, 'rio') and var_data.rio.crs is not None) else None
        
        try:
            stats = zonal_stats(
                track_data.geometry,
                raster_array,
                affine=affine_transform,
                nodata=nodata_value,
                all_touched=True,
                raster_out=True
            )
        except ValueError as e:
            raise ValueError(f"Zonal statistics calculation failed: {e}")

        # Extract values based on statistics parameter
        if stats_to_extract is None:
            # Extract all pixel values (default behavior)
            pixel_values_list = [
                res['mini_raster_array'].compressed().tolist() if res and res.get('mini_raster_array') is not None else []
                for res in stats
            ]
            track_data[var_name] = pixel_values_list
            track_data[var_name] = track_data[var_name].apply(lambda x: x if len(x) > 0 else np.nan)
        elif stats_to_extract is not None:
            # Extract specific statistics - ONLY when stats_to_extract is not None
            for stat_name in stats_to_extract:
                if stat_name == 'values':
                    col_values = f"{var_name}_values"

                    values_list = []
                    xy_list = [] if return_positions else None
                    coords_list = [] if return_positions else None
                    
                    # If return_positions is True, resample raster to tracking grid resolution
                    if return_positions and name_list:
                        # Check if we have lat/lon bounds in name_list
                        if all(key in name_list for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max', 'x_dim', 'y_dim']):
                            # Create affine transform for the tracking grid
                            tracking_affine = from_bounds(
                                name_list['lon_min'], 
                                name_list['lat_min'], 
                                name_list['lon_max'], 
                                name_list['lat_max'],
                                width=name_list['x_dim'], 
                                height=name_list['y_dim']
                            )
                            
                            # Create empty array for resampled raster
                            resampled_array = np.empty(
                                (name_list['y_dim'], name_list['x_dim']),
                                dtype=raster_array.dtype
                            )
                            
                            # Resample the raster to tracking grid
                            reproject(
                                source=raster_array,
                                destination=resampled_array,
                                src_transform=affine_transform,
                                src_crs='EPSG:4326',
                                dst_transform=tracking_affine,
                                dst_crs='EPSG:4326',
                                resampling=Resampling.nearest
                            )
                            
                            # Now use resampled array for zonal stats
                            stats_resampled = zonal_stats(
                                track_data.geometry,
                                resampled_array,
                                affine=tracking_affine,
                                nodata=nodata_value,
                                all_touched=True,
                                raster_out=True
                            )
                            
                            # Extract values and positions from resampled raster
                            for res in stats_resampled:
                                if res and res.get('mini_raster_array') is not None:
                                    arr = res['mini_raster_array']
                                    mask = ~arr.mask

                                    if np.any(mask):
                                        rows, cols = np.where(mask)
                                        vals = arr[rows, cols]
                                        values_list.append(vals.tolist())

                                        # Get the affine transform for the mini raster
                                        mini_affine = res.get('mini_raster_affine')
                                        
                                        if mini_affine is not None:
                                            # Convert local mini raster positions to spatial coordinates
                                            xs, ys = mini_affine * (cols, rows)
                                            
                                            # Store spatial coordinates
                                            coord_pairs = np.column_stack([xs, ys])
                                            coords_list.append(coord_pairs.tolist())
                                            
                                            # Convert spatial coordinates to pixel indices in tracking grid
                                            from rasterio.transform import rowcol
                                            pixel_rows, pixel_cols = rowcol(tracking_affine, xs, ys)
                                            
                                            # Convert to integers and store as [col, row] (x, y) convention
                                            pixel_cols = np.round(pixel_cols).astype(int)
                                            pixel_rows = np.round(pixel_rows).astype(int)
                                            xy_pairs = np.column_stack([pixel_cols, pixel_rows])
                                            xy_list.append(xy_pairs.tolist())
                                        else:
                                            xy_list.append(np.nan)
                                            coords_list.append(np.nan)
                                    else:
                                        values_list.append(np.nan)
                                        xy_list.append(np.nan)
                                        coords_list.append(np.nan)
                                else:
                                    values_list.append(np.nan)
                                    xy_list.append(np.nan)
                                    coords_list.append(np.nan)
                        else:
                            # Fallback to original method if tracking grid info not available
                            return_positions = False
                            print("Warning: Tracking grid information not available. Disabling position extraction.")
                    
                    # If return_positions is False or no tracking grid info, use original method
                    if not return_positions:
                        for res in stats:
                            if res and res.get('mini_raster_array') is not None:
                                arr = res['mini_raster_array']
                                mask = ~arr.mask

                                if np.any(mask):
                                    rows, cols = np.where(mask)
                                    vals = arr[rows, cols]
                                    values_list.append(vals.tolist())
                                else:
                                    values_list.append(np.nan)
                            else:
                                values_list.append(np.nan)

                    track_data[col_values] = values_list
                    
                    if return_positions and xy_list is not None:
                        col_xy = f"{var_name}_xy"
                        col_coords = f"{var_name}_coords"
                        track_data[col_xy] = xy_list
                        track_data[col_coords] = coords_list

                elif stat_name == 'mean':
                    col_name = f"{var_name}_{stat_name}"
                    values = [res.get('mean', np.nan) if res else np.nan for res in stats]
                    track_data[col_name] = values
                elif stat_name == 'median':
                    col_name = f"{var_name}_{stat_name}"
                    values = [np.median(res['mini_raster_array'].compressed()) if res and res.get('mini_raster_array') is not None else np.nan for res in stats]
                    track_data[col_name] = values
                elif stat_name == 'std':
                    col_name = f"{var_name}_{stat_name}"
                    values = [res.get('std', np.nan) if res else np.nan for res in stats]
                    track_data[col_name] = values
                elif stat_name == 'min':
                    col_name = f"{var_name}_{stat_name}"
                    values = [res.get('min', np.nan) if res else np.nan for res in stats]
                    track_data[col_name] = values
                elif stat_name == 'max':
                    col_name = f"{var_name}_{stat_name}"
                    values = [res.get('max', np.nan) if res else np.nan for res in stats]
                    track_data[col_name] = values
                elif stat_name == 'mode':
                    col_name = f"{var_name}_{stat_name}"
                    values = []
                    for res in stats:
                        if res and res.get('mini_raster_array') is not None:
                            compressed_array = res['mini_raster_array'].compressed()
                            if len(compressed_array) > 0:
                                mode_result = scipy_stats.mode(compressed_array, keepdims=True)
                                values.append(mode_result.mode[0])
                            else:
                                values.append(np.nan)
                        else:
                            values.append(np.nan)
                    track_data[col_name] = values
                elif stat_name == 'count':
                    col_name = f"{var_name}_{stat_name}"
                    values = [res.get('count', np.nan) if res else np.nan for res in stats]
                    track_data[col_name] = values
                elif stat_name.startswith('percentile_'):
                    # Extract percentile (e.g., 'percentile_25', 'percentile_75')
                    try:
                        percentile_value = float(stat_name.split('_')[1])
                        if not 0 <= percentile_value <= 100:
                            raise ValueError(f"Percentile must be between 0 and 100, got {percentile_value}")
                        col_name = f"{var_name}_{stat_name}"
                        values = []
                        for res in stats:
                            if res and res.get('mini_raster_array') is not None:
                                compressed_array = res['mini_raster_array'].compressed()
                                if len(compressed_array) > 0:
                                    values.append(np.percentile(compressed_array, percentile_value))
                                else:
                                    values.append(np.nan)
                            else:
                                values.append(np.nan)
                        track_data[col_name] = values
                    except (ValueError, IndexError) as e:
                        raise ValueError(f"Invalid percentile format: {stat_name}. Use 'percentile_X' where X is 0-100. Error: {e}")
                else:
                    raise ValueError(f"Unknown statistic: {stat_name}. Options are: values, mean, median, std, min, max, mode, count, percentile_X (e.g., percentile_25, percentile_75)")
    
    # Return geometry column to WKT for saving in parquet
    track_data['geometry'] = track_data['geometry'].apply(lambda geom: geom.wkt)
    
    # Save updated track data
    track_data.to_parquet(track_file)