import geopandas as gpd
from shapely.geometry import LineString
from pyfortracc.utilities.math_utils import uv_components

def split_mtd(cur_df, prv_df, spl_idx):
    """ 
    This method receive only events of Split and create a new vector for splited cells.
    The vector as created between the centroid of intersection
    of previous cell, and the centroid of current new splited cell.
    
    Parameters
    ----------
    cur_df : DataFrame
        current frame
    prev_df : DataFrame
        previous frame
    spl_idx : array
        array of indexes of splited cells
    
    Returns
    ----------
    linestrings : list
        list of LineStrings between centroids
    u_ : list 
        list of zonal (u) components
    v_ : list 
        list of meridional (v) components
    """
    # Set output
    linestrings, u_, v_ = [], [], []
    # Loop over spl_idx
    for sidx in spl_idx:
        cur_i_df = cur_df.loc[sidx]
        cur_geom = cur_i_df['geometry']
        prv_geom = prv_df.loc[cur_i_df['split_pr_idx']]['geometry']
        # if is a instance of GeoSeries get the first geometry
        if isinstance(cur_geom, gpd.GeoSeries):
            cur_geom = cur_geom.iloc[0]
        if isinstance(prv_geom, gpd.GeoSeries):
            prv_geom = prv_geom.iloc[0]
        # Get intersection between current and previous geometries
        prv_ints_ctrd = cur_geom.intersection(prv_geom).centroid
        cur_ctrd = cur_geom.centroid       
        linestrings.append(LineString([prv_ints_ctrd,cur_ctrd]))
        uv_ = uv_components(prv_ints_ctrd.coords[0], cur_ctrd.coords[0])
        u_.append(uv_[0])
        v_.append(uv_[1])
    return linestrings, u_, v_