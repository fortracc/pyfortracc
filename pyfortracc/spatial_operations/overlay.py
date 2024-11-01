def overlay_(cur_df, prv_df, min_overlap):
    """ 
    This function overlays two dataframes and returns the result.
    
    Parameters
    ----------
    cur_df : geopandas.GeoDataFrame
        Current dataframe.
    prv_df : geopandas.GeoDataFrame
        Previous dataframe.
    min_overlap : float
        Minimum overlap percentage.
        
    Returns
    -------
    overlays : geopandas.GeoDataFrame
        Dataframe with the overlays.
    """
    overlays = cur_df.reset_index().overlay(prv_df.reset_index(),
                                            how="intersection",
                                            keep_geom_type=True)
    overlays["ovrlp_area"] = overlays.area
    overlays["overlap"] = (overlays["ovrlp_area"] * 100) / overlays["size_1"]
    overlays = overlays.loc[overlays["overlap"] >= min_overlap]
    return overlays
