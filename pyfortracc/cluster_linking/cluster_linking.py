import pandas as pd
import pathlib
from pyfortracc.default_parameters import default_parameters
from pyfortracc.utilities.utils import (get_feature_files, create_dirs, 
                                        get_loading_bar, get_featstamp,
                                        set_schema, set_outputdf,
                                        read_parquet, write_parquet,
                                        check_operational_system)
from .new_frame import new_frame
from .max_uid import update_max_uid
from .board_clusters import board_clusters
from .refact_inside import refact_inside
from .merge_trajectory import merge_trajectory


def cluster_linking(name_lst):
    """
    The function links clusters over time, ensuring that clusters in different frames (representing different time points) 
    are identified and associated with each other based on spatial and temporal proximity.
    
    Parameters
    ----------
    name_lst : dict
        Dictionary with the parameters to be used.
    """
    print('Cluster linking:')
    # Set default parameters
    name_lst = default_parameters(name_lst)
    # Check operational system
    name_lst, _ = check_operational_system(name_lst, False)
    # Get feature files to be processed
    feat_path = name_lst['output_path'] + 'track/processing/spatial/'
    output_path = name_lst['output_path'] + 'track/processing/linked/'
    name_lst['output_spatial'] = output_path
    feat_files = get_feature_files(feat_path)
    create_dirs(output_path)
    loading_bar = get_loading_bar(feat_files)
    # Get number of prev_files to skip based on the number of prev_time
    prev_skip = name_lst['num_prev_skip']
    # Set delta_time
    dt_time = pd.Timedelta(minutes=name_lst['delta_time'])
    max_dt_time = pd.Timedelta(minutes=(name_lst['delta_time'] + 
                                        name_lst['delta_tolerance']))
    max_dt_time = max_dt_time * (prev_skip + 1)
    # Set initial uid if not set in the name_lst
    if 'initial_uid' not in name_lst.keys():
        name_lst['initial_uid'] = 1
    # Uid iterator is used to create new uids
    uid_iter = name_lst['initial_uid']
    # Set set_schema
    schema = set_schema('linked', name_lst)
    # Create empty previous frame
    prv_frame = pd.DataFrame()
    prv_stamp = get_featstamp(feat_files[0]) - dt_time
    # Set idx counter is used to create cindex
    cdx = 0
    for feat_time, feat_file in enumerate(feat_files):
        prv_frame, prv_stamp, uid_iter, cdx = linking((feat_time, feat_file, 
                                                prv_frame, prv_stamp,
                                                name_lst, uid_iter,
                                                max_dt_time, schema, cdx))
        loading_bar.update(1)
    loading_bar.close()
    return


def linking(args):
    """
    Links clusters between the current and previous frames, updates their unique identifiers (UIDs), 
    handles new frames, and saves the processed data.

    Parameters
    ----------
    args : tuple
        A tuple containing the following elements:
        - time_ (int): The current time step index.
        - cur_file (str): The path to the current frame's data file.
        - prv_frame (pandas.DataFrame): The DataFrame of the previous frame.
        - prv_stamp (pandas.Timestamp): The timestamp of the previous frame.
        - nm_lst (dict): A dictionary with necessary parameters (e.g., output paths, delta times, etc.).
        - uid_iter (int): The current UID iterator used to assign new UIDs.
        - max_dt (pandas.Timedelta): The maximum allowed time difference between frames.
        - schm (pandas.DataFrame): The schema for the output DataFrame.
        - icdx (int): The current index counter, which increments with each frame processed.

    Returns
    -------
    tuple
        A tuple containing the following elements:
        - cur_frame (pandas.DataFrame): The processed DataFrame of the current frame.
        - cur_stamp (pandas.Timestamp): The timestamp of the current frame.
        - uid_iter (int): The updated UID iterator.
        - icdx (int): The updated index counter.
    """
    time_, cur_file, prv_frame, prv_stamp, nm_lst, uid_iter, max_dt, schm, icdx = args
    # Read current file        print('Empty frame:', cur_file)
    cur_frame = read_parquet(cur_file, ['status','threshold_level',
                                        'past_idx','inside_idx',
                                        'board','board_idx',
                                        'trajectory'])
    # Set output file
    output_file = nm_lst['output_spatial'] + pathlib.Path(cur_file).name
    # Replace any /spatial/ in the output file path with /linked/
    output_file = output_file.replace('/spatial/', '/linked/')
    icdx += 1 # Increment cindex 
    #create columns 
    cur_frame['prv_mrg_uids'] = [None]*len(cur_frame)
    cur_frame['prv_mrg_iuids'] = [None]*len(cur_frame)
    cur_frame['prv_spl_uid'] = None
    cur_frame['prv_spl_iuid'] = None
    # Check if current frame is empty
    if cur_frame.empty:
        cur_frame['cindex'] = []
        cur_frame['uid'] = []
        if len(nm_lst['thresholds']) > 1:
            cur_frame['iuid'] = []
        cur_frame = cur_frame.astype({'cindex': 'int64', 'uid': 'int64'})
        # Calculate lifetime
        cur_frame['lifetime'] = []
        cur_frame['lifetime'] = cur_frame['lifetime'].fillna(0)
        write_parquet(cur_frame, output_file)
        return cur_frame, prv_stamp, uid_iter, icdx
    # Get schema and cols
    link_df = set_outputdf(schm)
    linked_cols = list(link_df.columns)
    # Create a column cal cindex based on the range of the current frame and assign
    # the value to the current frameprv_frame
    cdx_range = range(icdx, icdx + len(cur_frame))
    cur_frame['cindex'] = cdx_range
    cur_frame = pd.concat([cur_frame, link_df])
    # Get current stamp
    cur_stamp = get_featstamp(cur_file)
    # Calculate delta time
    dt_time = cur_stamp - prv_stamp
    # Conditions to enter in this conditional below:
    #   - time_ is 0
    #   - prv_frame is empty
    #   - dt_time is greater than max_dt
    if time_ == 0 or prv_frame.empty or dt_time > max_dt:
        # Classify clusters as new clusters and check board clusprv_frameters
        cur_frame = new_frame(cur_frame, uid_iter)
        # Find board clusters and find new frames
        if nm_lst['edges']:
            cur_frame = board_clusters(cur_frame)
            cur_frame = new_frame(cur_frame, uid_iter)
        # Refact inside clusters
        cur_frame = refact_inside(cur_frame, uid_iter)
        # Update max uid
        uid_iter = update_max_uid(cur_frame['uid'].max(), uid_iter)
        # Set lifetime equals to name_lst['delta_time']
        cur_frame['lifetime'] = nm_lst['delta_time']
        # Write linked file
        write_parquet(cur_frame[linked_cols], output_file)
        return cur_frame, cur_stamp, uid_iter, cdx_range[-1]
    # Get previous indx based for conditions:
    #  - prev_idx is not null
    #  - status is not NEW
    # The association values is based on prev_idx
    cur_prev_idx = cur_frame.loc[(~cur_frame['past_idx'].isnull())]
    cur_prev_idx = cur_prev_idx[~cur_prev_idx['status'].str.contains('NEW')]
    cur_idx = cur_prev_idx.index
    prv_idx = pd.Index(cur_prev_idx['past_idx'].values.astype(int))
    previous_uids = prv_frame.loc[prv_idx]['uid'].values
    previous_iuids = prv_frame.loc[prv_idx]['iuid'].values
    cur_frame.loc[cur_idx, 'uid'] = previous_uids
    cur_frame.loc[cur_idx, 'iuid'] = previous_iuids
    # merge uids and iuids
    
    if nm_lst['prv_uid']:
        mrg_frame = cur_frame.loc[(~cur_frame['merge_idx'].isnull())]
        if not mrg_frame.empty:
            mrg_frame[['prv_mrg_uids', 'prv_mrg_iuids']] = mrg_frame.apply(
                lambda x: pd.Series({
                    'prv_mrg_uids': prv_frame.loc[x['merge_idx'], 'uid'].to_list(),
                    'prv_mrg_iuids': prv_frame.loc[x['merge_idx'], 'iuid'].to_list()
                }),
                axis=1)
            cur_frame.loc[mrg_frame.index,['prv_mrg_uids', 'prv_mrg_iuids']] = mrg_frame[['prv_mrg_uids', 'prv_mrg_iuids']]
        # split uid and iuid
        spl_frame = cur_frame.loc[(~cur_frame['split_pr_idx'].isnull())]
        if not spl_frame.empty:
            spl_frame[['prv_spl_uid', 'prv_spl_iuid']] = spl_frame.apply(
                lambda x: pd.Series({
                    'prv_spl_uid': prv_frame.loc[x['split_pr_idx'], 'uid'],
                    'prv_spl_iuid': prv_frame.loc[x['split_pr_idx'], 'iuid']
                }),
                axis=1)
            cur_frame.loc[spl_frame.index,['prv_spl_uid', 'prv_spl_iuid']] = spl_frame[['prv_spl_uid', 'prv_spl_iuid']]
    # Merge trajectories
    cur_frame = merge_trajectory(cur_frame, cur_idx, prv_frame, prv_idx)
    # New frames for base threshold
    cur_frame = new_frame(cur_frame, uid_iter)
    # Check board clusters
    if nm_lst['edges']:
        cur_frame = board_clusters(cur_frame)
        cur_frame = new_frame(cur_frame, uid_iter)
    # Refact inside clusters
    cur_frame = refact_inside(cur_frame, uid_iter)
    # Update max uid
    uid_iter = update_max_uid(cur_frame['uid'].max(), uid_iter)
    # Calculate lifetime, get previous lifetime and add to current lifetime
    prev_lifetime = prv_frame.loc[prv_idx]['lifetime'].values
    # Calc time interval
    time_int = (cur_stamp - prv_stamp).total_seconds() / 60
    cur_frame.loc[cur_idx, 'lifetime'] = prev_lifetime + time_int
    # Split lifetime: Preserve lifetime of split clusters
    if nm_lst['preserv_split']:
        split_frs = cur_frame.loc[cur_frame['split_pr_idx'].notnull()]
        if len(split_frs) > 0:
            split_idx = split_frs['split_pr_idx'].values.astype(int)
            lifetimes = prv_frame.loc[split_idx]['lifetime']
            cur_frame.loc[split_frs.index, 'lifetime'] = lifetimes.values
    # Fill NaN values to 0
    cur_frame['lifetime'] = cur_frame['lifetime'].fillna(nm_lst['delta_time'])
    # Write linked file
    write_parquet(cur_frame[linked_cols], output_file)
    return cur_frame, cur_stamp, uid_iter, cdx_range[-1]
