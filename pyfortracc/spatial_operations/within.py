def within_(cur_df, prv_df):
    """ 
    This function whitin two dataframes and returns the result.
    
    Parameters
    ----------
    cur_df : geopandas.GeoDataFrame
        Current dataframe.
    prv_df : geopandas.GeoDataFrame
        Previous dataframe.
    
    Returns
    -------
    withins : geopandas.GeoDataFrame
        Dataframe with the result of the within operation.
    """
    withins = cur_df.sjoin(prv_df,
                            predicate="within",
                            lsuffix="1", rsuffix="2")
    withins.reset_index(inplace=True)
    withins.rename(columns={'index':'index_1'}, inplace=True)
    return withins