import pandas as pd
import numpy as np

def persistence_mean(track_df):
    """    Calculate the mean vector for each cluster in the track dataframe.
    This function computes the mean of the 'u_' and 'v_' components for each cluster
    identified by 'threshold_level' and 'uid'. It returns a DataFrame with the mean
    vectors.
    Parameters
    ----------
    track_df : pd.DataFrame
        The input track DataFrame containing 'u_' and 'v_' components.

    Returns
    -------
    pd.DataFrame
        A DataFrame with the mean vectors for each cluster.
    """

    # Calculate the mean vector for each cluster
    mean_vector = track_df.groupby(['threshold_level', 'uid']).agg(
        u_mean=('u_', lambda x: x.mean(skipna=True)),
        v_mean=('v_', lambda x: x.mean(skipna=True))
    ).reset_index()

    return mean_vector

def persistence(tracked_files, name_list):

    # Read the tracked files
    dfs = [pd.read_parquet(f) for f in tracked_files]
    track_df = pd.concat(dfs, ignore_index=True)

    # Define colunas de agrupamento
    if len(name_list['thresholds']) > 1:
        cluster_columns = ['threshold_level', 'uid', 'iuid']
        track_df['iuid'] = track_df['iuid'].where(track_df['iuid'].notna(), track_df['uid'])
        track_df['uid'] = track_df['iuid']

    # Get the latest timestamp
    last_timestamp = track_df['timestamp'].max()
    
    # Filter clusters that exist in the latest timestamp
    latest_clusters = track_df[track_df['timestamp'] == last_timestamp][cluster_columns].drop_duplicates().index
    # Drop the clusters not have u_ and v_ values
    latest_clusters = track_df.loc[latest_clusters].dropna(subset=['u_', 'v_']).index
    # Filter track_df to only include the latest timestamp based on the latest clusters but keep the values of other timestamps
    track_df = track_df[track_df[cluster_columns].apply(tuple, axis=1).isin(track_df.loc[latest_clusters, cluster_columns].apply(tuple, axis=1))]

    # Check if name_list have lat_min, lat_max, lon_min, lon_max is different from None
    if all(key in name_list and name_list[key] is not None for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
        # Convert u_ and v_ unints are in degrees to pixels
        track_df['u_'] = track_df['u_'] / name_list['y_res']
        track_df['v_'] = track_df['v_'] / name_list['x_res']

    # Get vectors to be used in the forecast
    forecast_vectors = persistence_mean(track_df)

    # Get only latest timestamp dataframe
    track_last = track_df[track_df['timestamp'] == last_timestamp]

    # Merge the mean vector with the latest timestamp dataframe
    track_last = track_last.merge(forecast_vectors, on=['threshold_level', 'uid'], how='left')

    # Apply the mean vector to the array_y and array_x columns
    track_last['array_y'] = track_last['array_y'] + track_last['u_mean']
    track_last['array_x'] = track_last['array_x'] + track_last['v_mean']

   # Clip the array_x and array_y values to the valid range
    track_last['array_x'] = track_last['array_x'].apply(
        lambda arr: np.clip([round(x) for x in arr], 0, name_list['x_dim'] - 1)
    )
    track_last['array_y'] = track_last['array_y'].apply(
        lambda arr: np.clip([round(y) for y in arr], 0, name_list['y_dim'] - 1)
    )

    # Check if edges are present in the name_list
    if 'edges' in name_list and name_list['edges']:
        # Send the board coordinates to the other side
        track_last['array_x'] = track_last['array_x'].apply(
            lambda arr: [x + name_list['x_dim'] if x < 0 else x for x in arr]
        )
        track_last['array_y'] = track_last['array_y'].apply(
            lambda arr: [y + name_list['y_dim'] if y < 0 else y for y in arr]
        )

    # Fill the forecast image with flattened array_y and array_x values
    array_y = np.concatenate(track_last['array_y'].values).astype(int)
    array_x = np.concatenate(track_last['array_x'].values).astype(int)
    values = np.concatenate(track_last['array_values'].values)

    # Map array_y and array_x to 1D indices
    h, w = name_list['y_dim'], name_list['x_dim']
    flat_idx = array_y * w + array_x  # Convert 2D indices to 1D indices

    # Sum of values for each position
    sum_image_flat = np.bincount(flat_idx, weights=values, minlength=h*w)

    # Count occurrences for each position
    count_image_flat = np.bincount(flat_idx, minlength=h*w)

    # Avoid division by zero
    with np.errstate(invalid='ignore', divide='ignore'):
        mean_image_flat = sum_image_flat / count_image_flat

    # Convert back to 2D image
    forecast_image = mean_image_flat.reshape((h, w))

    return forecast_image
 