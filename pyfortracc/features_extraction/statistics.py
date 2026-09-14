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
    # Group the polygons by cluster id. A cluster yields more than one polygon
    # when its pixels are not 8-connected, which happens with DBSCAN eps > 1.
    # Statistics must be computed once per cluster, not once per polygon,
    # otherwise the cluster points are replicated for every fragment.
    geometries = {}
    for geo, cluster_id in features.shapes(cluster_matrix,
                                        cluster_matrix != 0,
                                        connectivity=8,
                                        transform=(x_res, 0, lon_min,
                                                    0, y_res, lat_min)):
        # First coordinate set is exterior, rest are holes
        coordinates = geo['coordinates']
        boundary = Polygon(coordinates[0], coordinates[1:])
        geometries.setdefault(int(cluster_id), []).append(boundary)
    if not geometries:
        return pd.DataFrame()
    # Sort the points by cluster id once and slice each cluster from it
    labels = cluster_labels[:, 2]
    order = np.argsort(labels, kind='stable')
    ids, starts, counts = np.unique(labels[order], return_index=True,
                                    return_counts=True)
    slices = dict(zip(ids.tolist(), zip(starts.tolist(), counts.tolist())))
    # Cluster pixels are only kept if save_arrays is True
    save_arrays = name_list['save_arrays']
    columns = ['cluster_id', 'size', 'min', 'mean', 'max', 'std']
    if save_arrays:
        columns += ['array_values', 'array_x', 'array_y']
    stats = {col: [] for col in columns + ['geometry']}
    for cluster_id, boundaries in geometries.items():
        start, count = slices[cluster_id]
        cluster_indices = order[start:start + count]
        array_y = cluster_labels[cluster_indices, 0]
        array_x = cluster_labels[cluster_indices, 1]
        # Get array of values for the cluster
        cluster_values = values_matrix[array_y, array_x]
        if len(boundaries) == 1:
            boundary = boundaries[0]
        else:
            boundary = MultiPolygon(boundaries)
        # Check convex hull
        if name_list['convex_hull']:
            boundary = boundary.convex_hull
        stats['cluster_id'].append(cluster_id)
        stats['size'].append(len(cluster_values))
        stats['min'].append(np.nanmin(cluster_values))
        stats['mean'].append(np.nanmean(cluster_values))
        stats['max'].append(np.nanmax(cluster_values))
        stats['std'].append(np.nanstd(cluster_values))
        if save_arrays:
            stats['array_values'].append(cluster_values)
            stats['array_x'].append(array_x)
            stats['array_y'].append(array_y)
        stats['geometry'].append(boundary.wkt)
    # Build the dataframe at once. Array columns are built as object Series
    # so clusters of equal size are not stacked into a 2D array
    output_df = pd.DataFrame({
        col: pd.Series(values, dtype=object) if col.startswith('array_')
        else np.array(values)
        for col, values in stats.items()})
    return output_df
