def expansion(cur_df, prv_df, dt):
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
    # Get the size of the current and previous clusters:
    current_size = cur_df['size'].astype(int)
    previous_size = prv_df['size'].astype(int)
    #dt from minutes to seconds:
    dt = dt * 60
    
    # To calculate the normalized expansion rate of the area for a specific cluster i at time t, denoted as Norm expansion rate_i(t), use the average of the areas between two consecutive time steps:
    # equation (in 10-6 s-1): Norm expansion rate_i(t) = (1 / [(A_i(t) + A_i(t−1)) / 2]) * [(A_i(t) − A_i(t−1)) / dt]
    expansions = []
    for p,c in zip(previous_size, current_size):
        expansion = ((1 / ((c + p) / 2)) * ((c - p) / dt)) * 1e6
        expansions.append(expansion)

    return expansions