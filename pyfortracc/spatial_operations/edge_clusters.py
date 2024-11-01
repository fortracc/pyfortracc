import pandas as pd
import geopandas as gpd
from shapely import affinity

def edge_clusters(cur_df, left_edge, right_edge):
    """
    This function checks if any of the clusters in cur_df are touching the left 
    or right edge.
    
    Parameters
    ----------
    cur_df : GeoDataFrame
        current frame
    left_edge : GeoDataFrame
        left edge
    right_edge : GeoDataFrame
        right edge
    
    Returns
    ----------
    touch_larger : list
        list of clusters touching the right edge
    touch_lower : list
        list of clusters touching the left edge
    """
    # Set output
    touch_larger, touch_lower = [], []
    l_board = gpd.sjoin(cur_df, left_edge, how="inner", predicate="intersects")
    r_board = gpd.sjoin(cur_df, right_edge, how="inner", predicate="intersects")
    # Check if there is any intersected lef_board
    if r_board.empty and l_board.empty:
        return [], []
    # Get first point of left line
    left_coord = left_edge['geometry'].values[0].xy[0][0]
    # Send Geometries at right board to the left by affine transformation
    r_board['geometry'] = r_board['geometry'].apply(affinity.translate,
                                                    xoff=left_coord)
    # Merge left and right boards by touches
    touches = gpd.sjoin(l_board, r_board, how="inner", predicate="touches",
                        lsuffix="1", rsuffix="2")
    grouped_touches = touches.groupby(touches.index)
    for _, group in grouped_touches:
        g1 = group[['size_1']].reset_index().drop_duplicates()
        g1 = g1.rename(columns={'size_1':'size'})
        g2 = group[['index_2','size_2']]
        g2 = g2.rename(columns={'index_2':'index','size_2':'size'})
        mrg_g = pd.concat([g1,g2], ignore_index=True).set_index('index')
        # Get index of largest size using argmax
        largest_idx = mrg_g['size'].idxmax()
        # Get difference largest_idx and other indexes
        lowest_idx = mrg_g.loc[mrg_g.index != largest_idx].index.values
        # Multiply largest_idx based on the number of lowest_idx
        largest_idx = [largest_idx]*len(lowest_idx)
        # Append to output
        touch_larger.extend(largest_idx)
        touch_lower.extend(lowest_idx)
    return touch_larger, touch_lower
