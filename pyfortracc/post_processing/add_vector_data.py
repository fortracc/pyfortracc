import os
import glob
import pandas as pd
import geopandas as gpd
import multiprocessing as mp
from shapely.wkt import loads
from pyfortracc.utilities.utils import set_nworkers, get_loading_bar, check_operational_system


def add_vector_data(
    name_list,
    vector_path=None,
    vector_file_pattern=None,
    vector_column=None,
    track_column=None,
    merge_mode="fixed",
    time_tolerance=None,
    parallel=True
):
    """
    Add vector data to track files based on spatial overlay intersection.

    Parameters
    ----------
    name_list : dict
        A dictionary containing configuration parameters (from pyForTraCC).
    vector_path : str
        Path to the vector file or folder containing vector files.
    vector_file_pattern : str, optional
        Datetime pattern in vector filenames (e.g. '%Y%m%d.shp', '%Y%m%d_%H%M.gpkg').
        Required if using multiple vector files with temporal matching.
        Default is None.
    vector_column : str, optional
        Column name in the vector file to be used as the feature.
        Default is None.
    track_column : str, optional
        Column name in the tracking table to be updated with the feature.
        If None, uses the same name as `vector_column`. Default is None.
    merge_mode : str, default='fixed'
        Defines how to match vector files to tracks. Options:
            - 'fixed'    : Use the same vector file for all tracks (first file).
            - 'nearest'  : Select vector file closest in time to each track timestamp.
            - 'tolerance': Match vector files only if within `time_tolerance`.
    time_tolerance : str or pd.Timedelta, optional
        Maximum allowed time difference (e.g. '3H', '1D') for tolerance mode.
    parallel : bool, default=True
        Whether to enable parallel processing.
    """

    print("Adding vector data...")

    # --- Operational system checks ---
    name_list, parallel = check_operational_system(name_list, parallel)

    # --- Validation ---
    if vector_column is None:
        print("Error: vector_column cannot be None")
        return

    if vector_path is None:
        print("Error: vector_path cannot be None")
        return

    if not os.path.exists(vector_path):
        print(f"Error: Path does not exist or is incorrect: {vector_path}")
        return

    # If track_column is None, use the same name as vector_column
    if track_column is None:
        track_column = vector_column

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

    # --- Load vector files ---
    vector_path = vector_path.strip()
    if os.path.splitext(vector_path)[1]:
        # It's a single file
        search_pattern = vector_path
    else:
        # It's a folder
        search_pattern = os.path.join(vector_path, "*")

    vector_files = sorted(glob.glob(search_pattern, recursive=True))
    if not vector_files:
        print(f"No vector files found in {vector_path}")
        return

    # --- Merge logic depending on mode ---
    if merge_mode == "fixed":
        # Use the same vector file for all track files (first file)
        fixed_vector = vector_files[0]
        merged_df = track_df.copy()
        merged_df["vector_path"] = fixed_vector

    elif merge_mode == "nearest" or merge_mode == "tolerance":
        if vector_file_pattern is None:
            raise ValueError(
                f"You must specify `vector_file_pattern` for '{merge_mode}' mode "
                "(e.g. '%Y%m%d.shp', '%Y%m%d_%H%M.gpkg')"
            )

        # Parse vector file timestamps
        vector_timestamps = []
        valid_vector_files = []
        for f in vector_files:
            try:
                ts = pd.to_datetime(os.path.basename(f), format=vector_file_pattern)
                vector_timestamps.append(ts)
                valid_vector_files.append(f)
            except ValueError:
                # Skip files that don't match the pattern
                continue

        if not valid_vector_files:
            print(f"No vector files matching pattern '{vector_file_pattern}' found in {vector_path}")
            return

        vector_df = pd.DataFrame({"path": valid_vector_files}, index=vector_timestamps)

        if merge_mode == "nearest":
            merged_df = pd.merge_asof(
                track_df.sort_index(),
                vector_df.sort_index(),
                left_index=True,
                right_index=True,
                direction="nearest"
            )
            merged_df = merged_df.rename(columns={"path_y": "vector_path"}).drop(columns=["path_x"])
            merged_df = merged_df.rename(columns={"vector_path": "vector_path"})

        elif merge_mode == "tolerance":
            if time_tolerance is None:
                raise ValueError("You must specify `time_tolerance` for tolerance mode.")
            tolerance = pd.Timedelta(time_tolerance)
            merged_df = pd.merge_asof(
                track_df.sort_index(),
                vector_df.sort_index(),
                left_index=True,
                right_index=True,
                direction="nearest",
                tolerance=tolerance
            )
            merged_df = merged_df.dropna(subset=["path_y"]).rename(columns={"path_y": "vector_path"})
            merged_df = merged_df.drop(columns=["path_x"])

        else:
            raise ValueError("merge_mode must be one of: 'fixed', 'nearest', or 'tolerance'")

    else:
        raise ValueError("merge_mode must be one of: 'fixed', 'nearest', or 'tolerance'")

    # --- Process files ---
    n_workers = set_nworkers(name_list)
    loading_bar = get_loading_bar(track_files)

    # Transform merged_df to tuples for easier processing
    merged_list = merged_df[["path", "vector_path"]].itertuples(index=False, name=None)
    args_list = [(row[0], row[1], vector_column, track_column) for row in merged_list]

    # Parallel execution
    if parallel and n_workers > 1:
        with mp.Pool(n_workers) as pool:
            for _ in pool.imap_unordered(process_vector_file, args_list):
                loading_bar.update()
        loading_bar.close()
    else:
        for args in args_list:
            process_vector_file(args)
            loading_bar.update()
        loading_bar.close()


def process_vector_file(args):
    """
    Function executed for each track file to add vector data.

    Parameters
    ----------
    args : tuple
        A tuple containing the following elements:
        - track_file (str): The file path of the tracking table (parquet) to be updated.
        - vector_file (str): The file path of the vector file to overlay.
        - vector_column (str): The name of the column in the vector file containing the feature data.
        - track_column (str): The name of the column in the tracking table to be updated.

    Returns
    -------
    None
    """
    track_file, vector_file, vector_column, track_column = args

    # Load track data
    track_data = pd.read_parquet(track_file)

    # Load vector data
    try:
        gdf = gpd.read_file(vector_file)
    except Exception as e:
        print(f"Error reading vector file {vector_file}: {e}")
        return

    # Convert WKT geometry to GeoSeries
    track_geometries = gpd.GeoSeries(track_data["geometry"].apply(loads))
    track_gdf = track_geometries.to_frame().reset_index()
    track_gdf.columns = ["cindex", "geometry"]

    # Perform spatial overlay intersection
    try:
        overlay = gpd.overlay(track_gdf, gdf, how="intersection")
    except Exception as e:
        print(f"Error during overlay operation: {e}")
        return

    if overlay.empty:
        return

    # Calculate area of intersection
    overlay["area"] = overlay["geometry"].area

    # Classify based on largest area of intersection
    overlay = overlay.sort_values(by=["area"], ascending=False).drop_duplicates(
        subset=["cindex"], keep="first"
    )

    # Update track data with vector column values
    track_data.loc[overlay["cindex"].values, track_column] = overlay[vector_column].values

    # Save updated track data
    track_data.to_parquet(track_file)
