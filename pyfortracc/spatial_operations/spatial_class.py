import numpy as np
import pandas as pd


def continuous(operation):
    """ 
    Identify and retrieve information about continuous clusters.

    This function takes a DataFrame 'operation' as input, which is assumed to 
    have columns: 'cluster_id_1', 'cluster_id_2', 'index_1', and 'index_2'.
    It identifies and extracts clusters where each element appears only once in
    both 'cluster_id_1' and 'cluster_id_2'. The result is a pair of NumPy
    arrays, 'cont_indx_1' and 'cont_indx_2', containing the corresponding
    'index_1' and 'index_2' values for the identified continuous clusters.

    Parameters
    ----------
    operation : DataFrame
        Input is information about spatial operations.

    Returns
    ----------
    cont_indx_1 : array
        array containing 'index_1' for current frame
    cont_indx_2 : array
        array containing 'index_2' for previous frame
    """
    # Get continuous clusters, i.e. clusters that are present in both frames
    cont_cur = operation.groupby("cluster_id_1").filter(lambda group:
                                group["cluster_id_1"].count() == 1).index.values
    cont_past = operation.groupby("cluster_id_2").filter(lambda group:
                                group["cluster_id_2"].count() == 1).index.values
    # Get intersection of continuous clusters
    conts = np.intersect1d(cont_cur, cont_past)
    cont_indx_1 = operation.loc[conts]['index_1'].values
    cont_indx_2 = operation.loc[conts]['index_2'].values
    return cont_indx_1, cont_indx_2


def merge(operation):
    """ 
    Identify and retrieve information about merging clusters.

    This function takes a DataFrame 'operation' as input, which is assumed to
    have columns 'cluster_id_1', 'cluster_id_2', 'index_1', 'index_2', 'size_2'.
    It identifies clusters where the element in 'cluster_id_1' is duplicated 
    while not being null. The result is a set of NumPy arrays and a DataFrame
    containing information about the identified merging clusters.

    Parameters
    ----------
    operation : DataFrame
        Input DataFrame containing information about spatial operations.

    Returns
    ----------
    mergs_idx_1 : array
        array containing 'index_1' for current frame
    mergs_idx_2 : array
        array containing 'index_2' for previous frame
    merge_frame : DataFrame
        DataFrame containing detailed information about merging clusters,
    """
    mergs_ = np.array(operation[
                    (operation.duplicated(subset=["cluster_id_1"], keep=False))
                    & ~operation["cluster_id_1"].isnull()].index.values)
    mergs_idx_1 = operation.loc[mergs_]['index_1'].values
    mergs_idx_1 = np.unique(mergs_idx_1)
    # Add complete merge information
    merges_gp = operation.loc[mergs_][['index_1','index_2',
                                        'cluster_id_2','size_2']]
    merges_ids = merges_gp.groupby('index_1')['index_2'].apply(list)
    merges_ids = merges_ids.reset_index(name='merge_ids')
    merge_counts = merges_gp.groupby('index_1')['size_2'].apply(list)
    merge_counts = merge_counts.reset_index(name='merge_counts')
    mergMax = merges_gp.loc[merges_gp.groupby('index_1')['size_2'].idxmax()]
    mergMax = mergMax.reset_index()[['index_1','index_2','cluster_id_2']]
    merge_frame = pd.merge(merges_ids, merge_counts, on='index_1')
    merge_frame = pd.merge(merge_frame, mergMax, on='index_1')
    merge_frame = merge_frame.loc[merge_frame['index_1'].isin(mergs_idx_1)]
    mergs_idx_2 = merge_frame['index_2'].values
    return mergs_idx_1, mergs_idx_2, merge_frame


def split(operation):
    """ 
    Identify and retrieve information about splitting clusters.

    This function takes a DataFrame 'operation' as input, which is assumed to 
    have columns 'cluster_id_1', 'cluster_id_2', 'index_1', 'index_2', 'size_1'.
    It identifies clusters where the element in 'cluster_id_2' is duplicated
    while not being null. The result is a set of NumPy arrays containing 
    information about the identified splitting clusters.

    Parameters:
    - operation (DataFrame): Input DataFrame containing information about 
    spatial operations.

    Returns:
    - splits_idx (array): containing 'index_1' for current frame
    - split_prev_idx (array): containing 'index_2' for previous frame
    - new_splts_idx (array):  containing 'index_1' for cur frame are new splits
    - new_splts_prev_idx (array): containing 'index_2' previous are new splits
    """
    # Get splitting clusters, i.e. clusters that are present in both frames
    splits_ = np.array(operation[
                      (operation.duplicated(subset=["cluster_id_2"],keep=False))
                      & ~operation["cluster_id_2"].isnull()].index.values)
    splits_idx = operation.loc[splits_]['index_1'].values
    splits_idx = np.unique(splits_idx)
    splits_group = operation.loc[splits_][['index_1','index_2','cluster_id_1',
                                           'cluster_id_2','size_1']]
    splits_group = splits_group.groupby('cluster_id_2')
    splits_idx = []
    split_prev_idx = []
    new_splts_idx = []
    new_splts_prev_idx = []
    for _, sgroup in splits_group:
        max_count = sgroup['size_1'].max()
        max_idx = sgroup.loc[sgroup['size_1'] == max_count]['index_1'].values
        min_idx = sgroup.loc[sgroup['size_1'] != max_count]['index_1'].values
        splits_idx.append(max_idx[0])
        split_prev_idx.append(sgroup['index_2'].unique()[0])
        new_splts_idx.extend(min_idx)
        new_splts_prev_idx.extend([sgroup['index_2'].unique()[0]]*len(min_idx))
    # Convert lists to array
    splits_idx = np.array(splits_idx)
    split_prev_idx = np.array(split_prev_idx)
    new_splts_idx = np.array(new_splts_idx)
    new_splts_prev_idx = np.array(new_splts_prev_idx)
    return splits_idx, split_prev_idx, new_splts_idx, new_splts_prev_idx


def merge_split(mergs_idx_1, splits_idx_1, cur_frame, prev_frame):
    """ 
    Identify and retrieve information about merging and splitting clusters.

    This function takes the previous index arrays 'mergs_idx_1' and 'splits_idx_1'
    as input, along with the current and previous frames. It identifies the
    intersection of merging and splitting clusters and retrieves the 'index_2'
    values for the largest cluster in the previous frame. The result is a pair
    of NumPy arrays containing the 'index_1' and 'index_2' values for the
    identified merging and splitting clusters.

    Parameters
    ----------
    mergs_idx_1 : array
        array containing 'index_1' for current frame
    splits_idx_1 : array
        array containing 'index_1' for current frame
    cur_frame : DataFrame

    Returns
    ----------
    mergs_splits_idx : array
        array containing 'index_1' for current frame
    past_index : array
        array containing 'index_2' for previous frame
    """

    # Find intersection of merging and splitting clusters using set operations, find duplicated past_idx values
    cur_mrgsplt_idx = np.intersect1d(mergs_idx_1, splits_idx_1)
    past_index = []
    if len(cur_mrgsplt_idx) > 0:
        # For event in cur_mrgsplt_idx:
        for idx in cur_mrgsplt_idx:
            prv_idx = cur_frame.loc[idx][['split_pr_idx','merge_idx']].explode().dropna().values
            prv_idx = np.unique(prv_idx)
            # Get index of the largest cluster in the previous frame
            prv_idx = prev_frame.loc[prev_frame.index.isin(prv_idx)]['size'].idxmax()
            # Append to past_index
            past_index.append(prv_idx)
    return cur_mrgsplt_idx, past_index