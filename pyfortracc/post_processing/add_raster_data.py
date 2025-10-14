import os
import glob
import pandas as pd
import geopandas as gpd
import numpy as np
import multiprocessing as mp
from rasterstats import zonal_stats
from pyfortracc.utilities.utils import set_nworkers, get_loading_bar, check_operational_system

def add_raster_data(
    name_list,
    raster_function=None,
    raster_path=None,
    raster_file_pattern=None,
    column_name=None,
    merge_mode="nearest",
    time_tolerance=None,
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
    column_name : str
        Column name to store the raster-derived variable.
    merge_mode : str, default='nearest'
        Defines how to match rasters to tracks. Options:
            - 'nearest'  : Select raster closest in time to each track timestamp.
            - 'fixed'    : Use the same raster for all tracks (first or latest).
            - 'tolerance': Match rasters only if within `time_tolerance`.
    time_tolerance : str or pd.Timedelta, optional
        Maximum allowed time difference (e.g. '3H', '1D') for tolerance mode.
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
    
    # --- Process files ---
    n_workers = set_nworkers(name_list)
    # Loading bar
    loading_bar = get_loading_bar(track_files)

    # Transform merged_df to tuples for easier processing
    merged_list = merged_df[['path_x', 'path_y']].itertuples(index=False, name=None)
    args_list = [(row[0], row[1], column_name, raster_function) for row in merged_list]

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
    """Função executada para cada linha"""
    track_file, raster_file, column_name, raster_function = args

    # Load track data
    track_data = gpd.GeoDataFrame(
        pd.read_parquet(track_file),
        geometry=gpd.GeoSeries.from_wkt(pd.read_parquet(track_file)['geometry']),
        crs="EPSG:4326"
    )

    # Load raster data
    raster_data = raster_function(raster_file)

    # Compute zonal statistics
    stats = zonal_stats(
        track_data.geometry,
        raster_data.values,
        affine=raster_data.rio.transform() if hasattr(raster_data, 'rio') else None,
        nodata=raster_data.rio.nodata if hasattr(raster_data, 'rio') else None,
        all_touched=True,
        raster_out=True
    )

    # Extract pixel values from results
    pixel_values_list = [
        res['mini_raster_array'].compressed().tolist() if res and res.get('mini_raster_array') is not None else []
        for res in stats
    ]
    # Add pixel values to GeoDataFrame
    track_data[column_name] = pixel_values_list
    # If no values were found, fill with NaN
    track_data[column_name] = track_data[column_name].apply(lambda x: x if len(x) > 0 else np.nan)
    # Return geometry column to WKT for saving in parquet
    track_data['geometry'] = track_data['geometry'].apply(lambda geom: geom.wkt)
    
    # Save updated track data
    track_data.to_parquet(track_file)