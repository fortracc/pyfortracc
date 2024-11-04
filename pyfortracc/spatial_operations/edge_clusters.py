import pandas as pd
import geopandas as gpd
from shapely import affinity


def edge_clusters(cur_df, left_edge, right_edge, name_lst):
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
    # Check if there is any intersected right_board
    l_board = gpd.sjoin(cur_df, left_edge, how="inner", predicate="intersects")
    r_board = gpd.sjoin(cur_df, right_edge, how="inner", predicate="intersects")
    # Check if there is any intersected lef_board
    if r_board.empty and l_board.empty:
        return touch_larger, touch_lower
    # Get first point of left line to calculate the distance to the right board
    # left_coord = left_edge['geometry'].iloc[0].coords[0][0]
    rigth_coord = right_edge['geometry'].iloc[0].coords[0][0]
    if rigth_coord + name_lst['x_res'] > 180:
        rigth_coord = -360
    elif rigth_coord - name_lst['x_res'] < -180:
        rigth_coord = 360
    else:
        rigth_coord = 0

    # Send Geometries at right board to the left by affine transformation
    r_board['geometry'] = r_board['geometry'].apply(lambda x: affinity.translate(x,
                                                                                 xoff=rigth_coord,
                                                                                 yoff=0))
    
    # Apply buffer to avoid touching
    r_board['geometry'] = r_board['geometry'].buffer(name_lst['x_res'])
    # Apply buffer to avoid touching
    l_board['geometry'] = l_board['geometry'].buffer(name_lst['x_res'])

    # Merge left and right boards by touches
    touches = gpd.sjoin(l_board, r_board, how="inner", predicate="intersects",
                        lsuffix="1", rsuffix="2")
    
    # If there is no touch, return empty lists
    if touches.empty:
        return touch_larger, touch_lower

    # fig, ax = plt.subplots()
    # # left_edge.plot(ax=ax, color='yellow')
    # right_edge.plot(ax=ax, color='red')
    # l_board.plot(ax=ax, color='blue')
    # r_board.plot(ax=ax, color='green')
    # ax.set_ylim(25, 50)
    # ax.set_xlim(-182, -179)
    # plt.show()

    # Group touches by index
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
