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

def shifted_pixels(clusters, name_list):
    """
    Pixels of the clusters moved by their whole-pixel shift (columns dx, dy).

    Every pixel of a cluster gets the same shift, so the cluster keeps its shape. With
    name_list['edges'] the grid is periodic in x (global longitude); pixels moved out
    of the grid are dropped (never piled on the border).

    Returns
    -------
    (np.ndarray, np.ndarray)
        Flat indices of the moved pixels in the (y_dim, x_dim) grid and their values.
    """
    h, w = name_list['y_dim'], name_list['x_dim']
    if clusters.empty:
        return np.empty(0, dtype=np.int64), np.empty(0)
    n_pix = clusters['array_x'].map(len).to_numpy()
    xs = np.concatenate(clusters['array_x'].to_numpy()).astype(np.int64)
    ys = np.concatenate(clusters['array_y'].to_numpy()).astype(np.int64)
    values = np.concatenate(clusters['array_values'].to_numpy()).astype(float)
    xs = xs + np.repeat(clusters['dx'].to_numpy(), n_pix)
    ys = ys + np.repeat(clusters['dy'].to_numpy(), n_pix)
    if name_list.get('edges'):
        xs = xs % w
    keep = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h) & np.isfinite(values)
    return ys[keep] * w + xs[keep], values[keep]

def persistence(tracked_files, name_list):
    """
    Lagrangian persistence forecast of the next frame: every system of the last
    tracked frame is moved by the mean of its vectors over the observation window,
    keeping its shape, its size and its values.

    The systems are the clusters of the first threshold (uid). Each one is moved
    rigidly, with all its pixels, by a single whole-pixel shift (its mean vector,
    rounded half up), so the clusters of the other thresholds, which lie inside it,
    move with it and keep their place in the system. An inner cluster that lies
    outside every cluster of the first threshold (the outer one was below the
    minimum size) is moved, also rigidly, by its own mean vector. Where moved
    systems overlap, the forecast keeps the most intense value (the largest for
    the '>' operators, the smallest for '<', e.g. brightness temperature), so every
    system stays above its thresholds. Clusters without a vector at the last frame
    are not forecast.

    Parameters
    ----------
    tracked_files : list
        Tracking (or forecast) tables of the observation window, the last one being
        the frame the forecast starts from.
    name_list : dict
        The parameters of the tracking (y_dim, x_dim, operator, edges and, for
        vectors in degrees, x_res, y_res and the lat/lon bounds).

    Returns
    -------
    np.ndarray
        The forecast image (y_dim, x_dim); NaN where no system was moved.
    """

    # Read the tracked files
    dfs = [pd.read_parquet(f) for f in tracked_files]
    track_df = pd.concat(dfs, ignore_index=True)
    h, w = name_list['y_dim'], name_list['x_dim']
    forecast_image = np.full(h * w, np.nan)

    # Identity of a cluster: uid at the first threshold, iuid at the others
    if 'iuid' in track_df.columns:
        track_df['uid'] = track_df['iuid'].where(track_df['iuid'].notna(), track_df['uid'])

    # Convert u_ and v_ units from degrees to pixels. u_ is the zonal
    # (x/column) component and v_ the meridional (y/row) component
    if all(key in name_list and name_list[key] is not None for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
        track_df['u_'] = track_df['u_'] / name_list['x_res']
        track_df['v_'] = track_df['v_'] / name_list['y_res']

    # Clusters of the last frame and the mean vector of each one over the window
    last_timestamp = track_df['timestamp'].max()
    track_last = track_df[track_df['timestamp'] == last_timestamp]
    level0 = track_last['threshold_level'] == track_last['threshold_level'].min()
    systems = track_last[level0]
    inner = track_last[~level0]
    vectors = persistence_mean(track_df)

    # Inner clusters inside a system move with it; the others (orphans) on their own
    in_system = np.zeros(h * w, dtype=bool)
    if not systems.empty:
        in_system[np.concatenate(systems['array_y'].to_numpy()).astype(np.int64) * w +
                  np.concatenate(systems['array_x'].to_numpy()).astype(np.int64)] = True
    if not inner.empty:
        first_pixel = (inner['array_y'].map(lambda a: int(a[0])) * w +
                       inner['array_x'].map(lambda a: int(a[0]))).to_numpy()
        inner = inner[~in_system[first_pixel]]

    # Clusters with a vector at the last frame, shifted by their rounded mean vector
    moved = pd.concat([systems, inner], ignore_index=True)
    moved = moved[moved['u_'].notna() & moved['v_'].notna()]
    moved = moved.merge(vectors, on=['threshold_level', 'uid'], how='left')
    moved = moved.dropna(subset=['u_mean', 'v_mean'])
    if moved.empty:
        return forecast_image.reshape((h, w))
    moved['dx'] = np.floor(moved['u_mean'].to_numpy() + 0.5).astype(np.int64)
    moved['dy'] = np.floor(moved['v_mean'].to_numpy() + 0.5).astype(np.int64)
    flat_idx, values = shifted_pixels(moved, name_list)

    # Write the values so that the most intense one wins where moved systems overlap
    order = np.argsort(values, kind='stable')
    if str(name_list.get('operator', '>=')).startswith('<'):
        order = order[::-1]
    forecast_image[flat_idx[order]] = values[order]

    return forecast_image.reshape((h, w))
