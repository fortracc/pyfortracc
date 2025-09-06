import pandas as pd
import numpy as np
from rasterio import features
from shapely.geometry import Polygon, MultiPolygon
np.seterr(divide='ignore', invalid='ignore')


def geo_statistics(cluster_matrix, cluster_labels, values_matrix, name_list):
    """
    Calculate the statistics for each cluster

    parameters:
    ----------
    cluster_matrix: numpy array
        array with the clusters
    cluster_labels: numpy array
        array with the labels of the clusters
    values_matrix: numpy array
        array with the values

    returns:
    -------
    output_df: pandas dataframe
        dataframe with the statistics for each cluster
    """
    # Set output dataframe
    output_df = pd.DataFrame()
    # Set Mask
    mask = cluster_matrix != 0
    # Set y_, x_ coordinates and labels
    y_, x_ = cluster_labels[:, 0], cluster_labels[:, 1]
    labels = cluster_labels[:, 2]
    # Features.shapes returns a generator with the geometries
    # and the labels of the clusters
    # Connectiviy 8 is used to consider the diagonal neighbors
    # Transform is used to adjust the coordinates to the raster
    y_res = name_list['y_res']
    x_res = name_list['x_res']
    if name_list['lat_min'] is not None:
        lat_min = name_list['lat_min']
        lon_min = name_list['lon_min']
    else:
        lat_min = -0.5
        lon_min = -0.5
    # Loop over the generator to get the statistics for each cluster
    for geo in features.shapes(cluster_matrix,
                            mask,
                            connectivity=8,
                            transform=(x_res, 0, lon_min, 0, y_res, lat_min)):
        # Get the boundary of the cluster and the cluster id
        boundary = Polygon(geo[0]['coordinates'][0])
        cluster_id = int(geo[-1])
        # Get array of coordinates for the cluster
        # array_y, array_x = np.where(cluster_matrix == cluster_id)
        cluster_indices = np.argwhere(labels == cluster_id).ravel()
        array_y = y_[cluster_indices]
        array_x = x_[cluster_indices]
        # Get array of values for the cluster
        cluster_values = values_matrix[array_y, array_x]
        # Append the statistics to the dataframe
        cluster_stat = pd.DataFrame({'cluster_id': cluster_id,
                                    'size': [len(cluster_values)],
                                    'min': np.nanmin(cluster_values),
                                    'mean': np.nanmean(cluster_values),
                                    'max': np.nanmax(cluster_values),
                                    'std': np.nanstd(cluster_values),
                                    'array_values': [cluster_values],
                                    'array_x': [array_x],
                                    'array_y': [array_y],
                                    'geometry': boundary})
        # Append the statistics to the dataframe
        output_df = pd.concat([output_df, cluster_stat], axis=0)
    # Reset index
    output_df.reset_index(drop=True, inplace=True)
    # Get index of duplicated values at cluster_id column and groupby
    # This part is used to merge the clusters that are duplicated, the this is
    # occur when use eps parameter in DBSCAN > 1, and could merge clusters
    # with distance > eps
    if name_list['cluster_method'] == 'dbscan' and name_list['eps'] > 1:
        # Find duplicated values
        dupli_idx = output_df.duplicated(subset=['cluster_id'], keep=False)
        if not dupli_idx.any():
            # Check convex hull
            if name_list['convex_hull'] and len(output_df) > 0:
                output_df['geometry'] = output_df['geometry'].apply(lambda x: x.convex_hull)
            # Convert geometry to wkt
            if len(output_df) > 0: # Convert geometry to wkt
                output_df['geometry'] = output_df['geometry'].apply(lambda x: x.wkt)
            return output_df
        # Group by cluster_id
        dupli_group = output_df[dupli_idx].groupby('cluster_id')
        for _, group in dupli_group:
            multi_geo = MultiPolygon(list(group['geometry'].apply(Polygon)))
            m_array= np.concatenate(group['array_values'].values)
            m_array_x = np.concatenate(group['array_x'].values)
            m_array_y = np.concatenate(group['array_y'].values)
            output_df.loc[group.index[0], 'size'] = group['size'].sum()
            output_df.loc[group.index[0], 'min'] = group['min'].min()
            output_df.loc[group.index[0], 'mean'] = group['mean'].mean()
            output_df.loc[group.index[0], 'max'] = group['max'].max()
            output_df.loc[group.index[0], 'std'] = group['std'].mean()
            output_df.loc[group.index[0], 'geometry'] = multi_geo
            output_df.at[group.index[0], 'array_values'] = m_array
            output_df.at[group.index[0], 'array_x'] = m_array_x
            output_df.at[group.index[0], 'array_y'] = m_array_y
            output_df.drop(group.index[1:], inplace=True)
    # Check convex hull
    if name_list['convex_hull'] and len(output_df) > 0:
        output_df['geometry'] = output_df['geometry'].apply(lambda x: x.convex_hull)
    # Convert geometry to wkt
    if len(output_df) > 0:
        output_df['geometry'] = output_df['geometry'].apply(lambda x: x.wkt)
    return output_df
