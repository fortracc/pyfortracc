from shapely.geometry import LineString
from pyfortracc.utilities.math_utils import uv_components

def trajectory(cur_df, prev_df):
    """ 
    This function links two dataframes and returns the result.
    
    Parameters
    ----------
    cur_df : DataFrame
        current frame
    prev_df : DataFrame
        previous frame
    
    Returns
    ----------
    linestrings : list
        list of LineStrings between centroids
    u_ : list
        list of u components
    v_ : list
        list of v components
    """
    # Set output
    linestrings, u_, v_ = [], [], []
    # Get centroids of current clusters and previous clusters
    current_centroids = cur_df['centroid']
    previous_centroids = prev_df['centroid']
    for p,c in zip(previous_centroids, current_centroids):
        linestrings.append(LineString([p,c])) # LineString between centroids
        uv_ = uv_components(p.coords[0], c.coords[0])
        u_.append(uv_[0])
        v_.append(uv_[1])
    return linestrings, u_, v_