def expansion(cur_df, prv_trj, prv_df,dt,exp):
    """
    This function calculates the normalized expansion between two clusters.

    Parameters
    ----------
    cur_df : geopandas.GeoDataFrame
        Current dataframe.
    prv_df : geopandas.GeoDataFrame
        Previous dataframe.
    
    Returns
    -------
    expansion : float
        Normalized expansion between the two clusters.
    """
    expansions = []
    #dt from minutes to seconds:
    dt = dt * 60
    if exp: #check if condiniotal for expansion considers merges
        for i,row in cur_df.iterrows():
            if isinstance(row['merge_idx'], list):
                #Get the size of the current and previous clusters:
                p=prv_df.loc[row['merge_idx']]['size'].sum() 
                #Get the size of the current cluster:
                c=row['size']
            else:
                p=prv_df.loc[row['past_idx']]['size']
                c=row['size']
            expansion = ((1 / ((c + p) / 2)) * ((c - p) / dt)) * 1e6
            expansions.append(expansion)
    else:
        #Get the size of the current and previous clusters:
        current_size = cur_df['size'].astype(int)
        previous_size = prv_trj['size'].astype(int)
        # To calculate the normalized expansion rate of the area for a specific cluster i at time t, denoted as Norm expansion rate_i(t), use the average of the areas between two consecutive time steps:
        # equation (in 10-6 s-1): Norm expansion rate_i(t) = (1 / [(A_i(t) + A_i(t−1)) / 2]) * [(A_i(t) − A_i(t−1)) / dt]
        for p,c in zip(previous_size, current_size):
            expansion = ((1 / ((c + p) / 2)) * ((c - p) / dt)) * 1e6
            expansions.append(expansion)
    return expansions