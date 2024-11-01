def contains_(cur_df, prv_df):
    """
    This function contains two dataframes and returns the result.
    
    Parameters
    ----------
    cur_df : geopandas.GeoDataFrame
        Current dataframe.
    prv_df : geopandas.GeoDataFrame
        Previous dataframe.
        
    Returns
    -------
    contains : geopandas.GeoDataFrame
        Dataframe with the result of the contains operation.
    """
    
    contains = prv_df.sjoin(cur_df,
                            predicate="contains",
                            lsuffix="2", rsuffix="1")
    contains.reset_index(inplace=True)
    contains.rename(columns={'index':'index_2'}, inplace=True)
    contains.rename(columns={'index':'index_1'}, inplace=True)
    return contains