import os
import glob
import pandas as pd
import geopandas as gpd
import numpy as np
import multiprocessing as mp
from scipy import stats as scipy_stats
from rasterstats import zonal_stats
from rasterio.transform import from_bounds, from_origin, rowcol
from rasterio.warp import reproject, Resampling
from pyfortracc.utilities.utils import (set_nworkers, get_loading_bar, check_operational_system,
                                        get_featstamp)

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
    raster_function : callable
        Function that receives a raster file path and returns an xarray DataArray or Dataset with
        1-D 'lat' and 'lon' coordinates (pixel centres of a regular grid, in any order) and a CRS.
    raster_path : str
        Path to raster data folder or files.
    raster_file_pattern : str
        Datetime pattern in raster filenames (e.g. '%Y.tif', '%Y%m%d_%H%M.nc').
        Not needed in 'fixed' mode.
    merge_mode : str, default='nearest'
        Defines how to match rasters to tracks. Options:
            - 'nearest'  : Select raster closest in time to each track timestamp.
            - 'fixed'    : Use the same raster (the first file) for all tracks.
            - 'tolerance': Match rasters only if within `time_tolerance`. Tracks without a
                           raster get the new columns with no data (NaN; count = 0).
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

    # Tracking tables are named YYYYMMDD_HHMM.parquet
    track_timestamps = [pd.Timestamp(get_featstamp(f)) for f in track_files]
    track_df = pd.DataFrame({"track_path": track_files}, index=track_timestamps).sort_index()

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

    # --- Merge logic depending on mode ---
    if merge_mode == "fixed":
        # Use the same raster for all track files
        merged_df = track_df.assign(raster_path=raster_files[0])

    elif merge_mode in ("nearest", "tolerance"):
        if raster_file_pattern is None:
            raise ValueError(f"You must specify `raster_file_pattern` for '{merge_mode}' mode.")
        if merge_mode == "tolerance" and time_tolerance is None:
            raise ValueError("You must specify `time_tolerance` for tolerance mode.")
        raster_timestamps = [
            pd.to_datetime(os.path.basename(f), format=raster_file_pattern)
            for f in raster_files
        ]
        raster_df = pd.DataFrame({"raster_path": raster_files}, index=raster_timestamps).sort_index()
        merged_df = pd.merge_asof(
            track_df,
            raster_df,
            left_index=True,
            right_index=True,
            direction="nearest",
            tolerance=pd.Timedelta(time_tolerance) if merge_mode == "tolerance" else None
        )
        # Tracks without a raster within the tolerance get the new columns with no data
        merged_df["raster_path"] = merged_df["raster_path"].astype(object).where(merged_df["raster_path"].notna(), None)
        n_missing = merged_df["raster_path"].isna().sum()
        if n_missing:
            print(f"{n_missing} track files without a raster within {time_tolerance}: new columns with no data")

    else:
        raise ValueError("merge_mode must be one of: 'nearest', 'fixed', or 'tolerance'")

    # open first raster file to check its structure
    sample_raster = raster_files[0]
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
    merged_list = merged_df[['track_path', 'raster_path']].itertuples(index=False, name=None)
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


def raster_grid(var_data):
    """
    North-up array and affine transform of a raster with 1-D 'lat' and 'lon' coordinates.

    The coordinates are the pixel centres of a regular grid, in any order (latitude ascending
    rasters are flipped, longitude descending rasters are reversed). The transform places the
    outer pixel edges half a pixel beyond the first and last centres.

    Parameters
    ----------
    var_data : xarray.DataArray
        Raster with 'lat' and 'lon' dimensions (at least 2 pixels in each).

    Returns
    -------
    raster_array : np.ndarray
        Array with rows from north to south and columns from west to east.
    affine_transform : affine.Affine
        Transform of `raster_array`.
    """
    var_data = var_data.transpose('lat', 'lon', ...)
    lon = var_data.coords['lon'].values.astype('float64')
    lat = var_data.coords['lat'].values.astype('float64')
    if len(lon) < 2 or len(lat) < 2:
        raise ValueError(f"Raster must have at least 2 pixels in 'lat' and 'lon': lat={len(lat)}, lon={len(lon)}")
    if lon[0] > lon[-1]:
        var_data, lon = var_data.isel(lon=slice(None, None, -1)), lon[::-1]
    if lat[0] < lat[-1]:
        var_data, lat = var_data.isel(lat=slice(None, None, -1)), lat[::-1]
    x_res = (lon[-1] - lon[0]) / (len(lon) - 1)
    y_res = (lat[0] - lat[-1]) / (len(lat) - 1)
    if not (np.allclose(np.diff(lon), x_res, rtol=1e-3, atol=0) and
            np.allclose(-np.diff(lat), y_res, rtol=1e-3, atol=0)):
        raise ValueError("Raster 'lat' and 'lon' coordinates must be regularly spaced (pixel centres).")
    affine_transform = from_origin(lon[0] - x_res / 2, lat[0] + y_res / 2, x_res, y_res)
    return var_data.values, affine_transform


def statistics_columns(var_2d, stats_to_extract, return_positions):
    """
    Names and dtypes of the columns created by process_file (used for frames without
    clusters or without a raster, so every tracking file gets the same columns).
    """
    columns = {}
    for var_name in var_2d:
        if stats_to_extract is None:
            columns[var_name] = 'object'
            continue
        for stat_name in stats_to_extract:
            if stat_name == 'values':
                columns[f"{var_name}_values"] = 'object'
                if return_positions:
                    columns[f"{var_name}_xy"] = 'object'
                    columns[f"{var_name}_coords"] = 'object'
            elif stat_name == 'count':
                columns[f"{var_name}_count"] = 'int64'
            else:
                columns[f"{var_name}_{stat_name}"] = 'float64'
    return columns


def process_file(args):
    """
    Function executed for each line of track and raster file pair.

    `raster_file` None means no raster for this track file (tolerance mode): the new columns
    are written with no data (NaN; count = 0).
    """

    track_file, raster_file, var_2d, raster_function, statistics, return_positions, name_list = args

    # Load track data
    track_data = pd.read_parquet(track_file)

    # Normalize statistics parameter
    if statistics is None or statistics == 'pixels':
        stats_to_extract = None  # Extract all pixel values
    elif isinstance(statistics, str):
        stats_to_extract = [statistics]
    else:
        stats_to_extract = statistics
    columns = statistics_columns(var_2d, stats_to_extract, return_positions)

    # Frames without clusters or without a raster: same columns, no data
    if track_data.empty or raster_file is None:
        for col, dtype in columns.items():
            if dtype == 'int64':
                track_data[col] = pd.Series(0, index=track_data.index, dtype='int64')
            else:
                track_data[col] = pd.Series(np.nan, index=track_data.index, dtype=dtype)
        track_data.to_parquet(track_file)
        return

    geometries = gpd.GeoSeries.from_wkt(track_data['geometry'], crs="EPSG:4326")

    # Load raster data
    raster_data = raster_function(raster_file)

    # Process each 2D variable
    for var_name in var_2d:
        # If it's a DataArray, access directly; if it's a Dataset, use the variable name
        if hasattr(raster_data, 'data_vars'):
            # It's a Dataset
            var_data = raster_data[var_name]
        else:
            # It's a DataArray
            var_data = raster_data

        if 'lon' not in var_data.coords or 'lat' not in var_data.coords:
            raise ValueError("Cannot determine affine transform from raster data")

        # North-up array and transform from the pixel-centre coordinates
        raster_array, affine_transform = raster_grid(var_data)

        # Check if array has valid dimensions
        if raster_array.ndim < 2 or min(raster_array.shape[:2]) == 0:
            raise ValueError(f"Invalid raster dimensions: {raster_array.shape}. Must be at least 2D with both dimensions > 0")

        # Get nodata value from rio if available, otherwise None
        nodata_value = var_data.rio.nodata if (hasattr(var_data, 'rio') and var_data.rio.crs is not None) else None

        try:
            stats = zonal_stats(
                geometries,
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

                            # Resampled raster: pixels outside the source raster are no data
                            # (NaN for float rasters without a nodata value)
                            fill_value = nodata_value
                            if fill_value is None and np.issubdtype(raster_array.dtype, np.floating):
                                fill_value = np.nan
                            resampled_array = np.full(
                                (name_list['y_dim'], name_list['x_dim']),
                                0 if fill_value is None else fill_value,
                                dtype=raster_array.dtype
                            )

                            # Resample the raster to tracking grid
                            reproject(
                                source=raster_array,
                                destination=resampled_array,
                                src_transform=affine_transform,
                                src_crs='EPSG:4326',
                                src_nodata=fill_value,
                                dst_transform=tracking_affine,
                                dst_crs='EPSG:4326',
                                dst_nodata=fill_value,
                                resampling=Resampling.nearest
                            )

                            # Now use resampled array for zonal stats
                            stats_resampled = zonal_stats(
                                geometries,
                                resampled_array,
                                affine=tracking_affine,
                                nodata=fill_value,
                                all_touched=True,
                                raster_out=True
                            )

                            # Extract values and positions from resampled raster
                            for res in stats_resampled:
                                if res and res.get('mini_raster_array') is not None:
                                    arr = res['mini_raster_array']
                                    mask = ~np.ma.getmaskarray(arr)

                                    if np.any(mask):
                                        rows, cols = np.where(mask)
                                        vals = arr[rows, cols]
                                        values_list.append(np.asarray(vals).tolist())

                                        # Get the affine transform for the mini raster
                                        mini_affine = res.get('mini_raster_affine')

                                        if mini_affine is not None:
                                            # Spatial coordinates of the pixel centres
                                            xs, ys = mini_affine * (cols + 0.5, rows + 0.5)

                                            # Store spatial coordinates
                                            coord_pairs = np.column_stack([xs, ys])
                                            coords_list.append(coord_pairs.tolist())

                                            # Pixel indices of the centres in the tracking grid (row 0 = north)
                                            pixel_rows, pixel_cols = rowcol(tracking_affine, xs, ys)

                                            # Store as [col, row] (x, y) convention
                                            xy_pairs = np.column_stack([np.asarray(pixel_cols, dtype=int),
                                                                        np.asarray(pixel_rows, dtype=int)])
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
                                mask = ~np.ma.getmaskarray(arr)

                                if np.any(mask):
                                    rows, cols = np.where(mask)
                                    vals = arr[rows, cols]
                                    values_list.append(np.asarray(vals).tolist())
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
                    values = []
                    for res in stats:
                        compressed_array = res['mini_raster_array'].compressed() if res and res.get('mini_raster_array') is not None else []
                        values.append(np.median(compressed_array) if len(compressed_array) > 0 else np.nan)
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
                    values = [res.get('count', 0) if res else 0 for res in stats]
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

    # Same dtypes in every file (rasterstats returns None for clusters without valid pixels)
    for col, dtype in columns.items():
        if dtype != 'object':
            track_data[col] = pd.to_numeric(track_data[col].astype(object).where(track_data[col].notna(), np.nan)).astype(dtype)

    # Save updated track data (plain parquet, geometry kept as WKT as in the tracking)
    track_data.to_parquet(track_file)
