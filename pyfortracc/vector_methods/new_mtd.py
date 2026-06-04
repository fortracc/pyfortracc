import numpy as np
from scipy.spatial import cKDTree
from pyfortracc.utilities.math_utils import calc_mean_uv


def new_mtd(cur_df, new_idx, num_neighbors=3):
    """
    This method receives only events of type NEW (clusters that have no
    previous match and therefore no displacement vector) and creates a new
    vector for them. The vector is estimated as the mean of the displacement
    vectors of the nearest neighbouring clusters that already have a valid
    vector, ensuring a larger amount of vectors over the field.

    A KD-tree is built over the centroids of the donor clusters (the ones that
    already carry a vector), so the nearest-neighbour search runs in
    O(N log N), keeping the method computationally efficient even for frames
    with many clusters.

    Parameters
    ----------
    cur_df : GeoDataFrame
        current frame, already containing the base vectors (u_, v_) computed
        for the matched clusters.
    new_idx : array-like
        array of indexes of the NEW clusters to be filled.
    num_neighbors : int
        maximum number of nearest neighbours used to average the vector.

    Returns
    -------
    idx_ : list
        list of indexes of NEW clusters that received a vector.
    u_ : list
        list of zonal (u) components.
    v_ : list
        list of meridional (v) components.

    Notes
    -------
    u : float
        The zonal component, representing the east-west direction (zonal).
    v : float
        The meridional component, representing the north-south direction (meridional).
    """
    # Set output
    idx_, u_, v_ = [], [], []
    # Donor clusters are the ones that already have a valid base vector
    donors = cur_df.loc[cur_df['u_'].notna() & cur_df['v_'].notna()]
    # Need at least one donor and one NEW cluster to estimate a vector
    if len(donors) == 0 or len(new_idx) == 0:
        return idx_, u_, v_
    # Build coordinate and vector arrays from the donor centroids
    donor_xy = np.array([(c.x, c.y) for c in donors['centroid'].values])
    donor_uv = donors[['u_', 'v_']].to_numpy(dtype=float)
    # Build coordinate array from the NEW cluster centroids
    new_clusters = cur_df.loc[new_idx]
    new_xy = np.array([(c.x, c.y) for c in new_clusters['centroid'].values])
    # Query the k nearest donors for each NEW cluster (k bounded by donors available)
    k = min(num_neighbors, len(donors))
    tree = cKDTree(donor_xy)
    _, nn_idx = tree.query(new_xy, k=k)
    # Ensure 2D shape (n_new, k) even when k == 1
    nn_idx = nn_idx.reshape(len(new_xy), k)
    # Mean of the neighbour vectors for each NEW cluster
    for ridx, neighbors in zip(new_clusters.index, nn_idx):
        mean_uv = calc_mean_uv(donor_uv[neighbors])
        idx_.append(ridx)
        u_.append(mean_uv[0])
        v_.append(mean_uv[1])
    return idx_, u_, v_
