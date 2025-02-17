import numpy as np
from scipy import ndimage
from sklearn.cluster import DBSCAN


def clustering(mtd, data, operator, thld, min_size, eps=None):
    """
    Return the cluster labels for each point based on the method used

    Parameters:
    ----------
    mtd: mtd string
        method to be used to cluster the data
    name_list: dictionary
        dictionary with the parameters
    data: numpy array
        array of data to be clustered
    operator: function
        function to be used to thresholding segmentation
    thld: float
        threshold value
    min_size: int
        minimum number of points per cluster
    Returns:
    -------
    clusters: numpy array
        array of clusters (x, y, label)
    """
    if mtd == 'dbscan':
        clusters, labels = dbscan_clustering(data, operator, thld, min_size,
                                            eps=eps)
    elif mtd == 'ndimage':
        clusters, labels = ndimage_clustering(data, operator, thld, min_size,
                                            eps=eps)
    else:
        raise ValueError('Invalid cluster method')
    return clusters, labels


def dbscan_clustering(data, operator, threshold, min_size, eps=1):
    """
    Return the cluster labels for each point

    parameters:
    ----------
    data: numpy matrix
        matrix of data
    operator: function
        function to be used to thresholding segmentation
    threshold: float
        threshold value
    min_size: int
        minimum number of points per cluster

    returns:
    ------
    labels: numpy matrix
        matrix with the clusters
    """
    # Segment the data based on the threshold
    points = np.argwhere(operator(data, threshold))
    # Set the dbscan object
    dbscan = DBSCAN(algorithm='kd_tree', metric='chebyshev',
                    eps=eps, min_samples=3)
    # Fit the dbscan model
    dbscan.fit(points)
    labels = np.concatenate((points, dbscan.labels_[:, np.newaxis]), axis=1)
    # Remove noise
    labels = labels[labels[:, -1] != -1]
    # Increment label to start from 1
    labels[:, -1] += 1
    # Filter by count of points labels
    items, count = np.unique(labels[:, -1], return_counts=True)
    filter_ids = items[count < min_size]
    # Remove points with less than min_cluster_size points
    labels = labels[~np.isin(labels[:, -1], filter_ids)]
    # Cluster matrix are the same size as the data and filled with nan
    clusters = np.zeros(data.shape, dtype=np.int32)
    # Fill the cluster matrix with the labels
    clusters[labels[:, 0], labels[:, 1]] = labels[:, -1]
    return clusters, labels


def ndimage_clustering(data, operator, threshold, min_size, eps=None):
    """
    Return the cluster labels for each point

    parameters:
    ----------
    data: numpy matrix
        matrix of data
    operator: function
        function to be used to thresholding segmentation
    threshold: float
        threshold value
    min_size: int
        minimum number of points per cluster

    returns:
    ------
    labels: numpy matrix
        matrix with the clusters
    """
    mask = operator(data, threshold)
    structure_von_neumann = [[1, 1, 1],
                             [1, 1, 1],
                             [1, 1, 1]]
    clusters, numL = ndimage.label(mask, structure_von_neumann)
    sizes = ndimage.sum(mask, clusters, range(numL + 1))
    mask_size = sizes < min_size
    remove_pixel = mask_size[clusters]
    clusters[remove_pixel] = 0
    # Get positions of clusters and labels
    labels = np.argwhere(clusters != 0)
    # Get the id of the clusters and add to the labels
    labels = np.concatenate((labels, clusters[clusters != 0][:, np.newaxis]),
                            axis=1)
    return clusters, labels
