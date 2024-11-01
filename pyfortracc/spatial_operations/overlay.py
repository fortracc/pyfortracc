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
    # Caclulate the area of the current dataframe
    cur_df['cur_area'] = cur_df.area
    # Overlay the dataframes
    overlays = cur_df.reset_index().overlay(prv_df.reset_index(),
                                            how="intersection",
                                            keep_geom_type=True)
    # Calculate the area of the overlays
    overlays["ovrlp_area"] = overlays.area
    # Calculate the overlap percentage
    overlays["overlap"] = (overlays["ovrlp_area"] * 100) / overlays["cur_area"]
    # Filter the overlays based on the minimum
    overlays = overlays.loc[overlays["overlap"] >= min_overlap]
    return overlays
