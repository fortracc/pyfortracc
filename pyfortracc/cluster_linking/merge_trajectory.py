from shapely.wkt import loads
from shapely.ops import linemerge


def merge_trajectory(cur_frame, cur_idx, prv_frame, prv_idx):
    """
    Merge trajectories from previous and current frames into a single trajectory.

    This function merges line trajectories from two GeoDataFrames, `cur_frame` (current frame) and 
    `prv_frame` (previous frame), based on matching indices. It combines the trajectories from both 
    frames if they are valid (i.e., not empty or invalid geometries) and updates the current frame 
    with the merged trajectory.

    Parameters
    ----------
    cur_frame : GeoDataFrame
        The current frame containing trajectories and corresponding indices.
    cur_idx : list or array-like
        The indices of the trajectories in the current frame to be considered for merging.
    prv_frame : GeoDataFrame
        The previous frame containing trajectories.
    prv_idx : list or array-like
        The indices of the trajectories in the previous frame to be considered for merging.

    Returns
    -------
    GeoDataFrame
        The updated current frame with merged trajectories where applicable.

    Notes
    -----
    - The function assumes that the trajectories are stored as `LineString` geometries.
    - Empty or invalid geometries (e.g., 'LINESTRING EMPTY' or 'GEOMETRYCOLLECTION EMPTY') are filtered out before merging.
    - The merging process uses the Shapely `loads` function to parse WKT strings into geometric objects.
    - The resulting merged trajectory is stored back in the `trajectory` column of `cur_frame`.
    """
    # Get the current and previous trajectories
    cur_traj = cur_frame.loc[cur_idx][['trajectory','past_idx']]   
    cur_traj = cur_traj[cur_traj['trajectory'] != 'LINESTRING EMPTY']
    cur_traj = cur_traj.reset_index()
    cur_traj = cur_traj.rename(columns={'index':'index_c',
                                        'trajectory':'cur_traj'})
    cur_traj.set_index('past_idx', inplace=True)
    prv_traj = prv_frame.loc[prv_idx][['trajectory']]
    prv_traj = prv_traj.rename(columns={'trajectory':'prev_traj'})
    # Merge trajectories
    merged = cur_traj.merge(prv_traj, left_index=True, right_index=True)
    merged = merged[(merged['prev_traj'] != 'LINESTRING EMPTY') &
                    (merged['prev_traj'] != 'GEOMETRYCOLLECTION EMPTY')]
    merged['prev_traj'] = merged['prev_traj'].apply(loads)
    merged['cur_traj'] = merged['cur_traj'].apply(loads)
    if not merged.empty: # Check if merged not empty
        merged['trajectory'] = merged.apply(merge_lines, axis=1)
        mrgd_trj = merged['trajectory'].values.astype(str)
        cur_frame.loc[merged.index_c,'trajectory'] = mrgd_trj
    return cur_frame

    
def merge_lines(row):
    """
    Merge lines from previous and current frames into a single trajectory.

    This function merges the current and previous line trajectories provided in a row of a DataFrame or GeoDataFrame.
    The current trajectory is expected to be a `LineString`, while the previous trajectory can be either a `LineString`
    or a `MultiLineString`. The merged result is a single geometry that represents the combined trajectory.

    Parameters
    ----------
    row : pandas.Series or GeoPandas.GeoSeries
        A row containing the 'cur_traj' and 'prev_traj' geometries to be merged.

    Returns
    -------
    shapely.geometry.LineString or shapely.geometry.MultiLineString
        The merged trajectory as a `LineString` or `MultiLineString`, depending on the input geometries.

    Notes
    -----
    - The function uses the Shapely `linemerge` function to combine the geometries.
    - If the previous trajectory (`prev_traj`) is a `LineString`, it is converted to a list for merging.
    - If the previous trajectory is a `MultiLineString`, it is decomposed into individual `LineString` geometries before merging with the current trajectory.
    """
    cur_lines, prev_lines = [row.cur_traj], row.prev_traj
    if prev_lines.geom_type == 'LineString':
        prev_lines = [prev_lines]
    elif prev_lines.geom_type == 'MultiLineString':
        prev_lines = [line for line in prev_lines.geoms]
    to_merge = prev_lines + cur_lines
    return linemerge(to_merge)
