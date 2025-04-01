import pandas as pd
import numpy as np
import pathlib
from multiprocessing import Pool
from shapely.geometry import LineString
from shapely.wkt import loads
from pyfortracc.default_parameters import default_parameters
from pyfortracc.utilities.utils import (get_feature_files, get_edges,
                                        get_loading_bar, get_previous_file,
                                        get_previous_proccessed_files,
                                        check_operational_system,
                                        get_geotransform, set_nworkers, 
                                        create_dirs, set_schema, set_outputdf,
                                        read_parquet, write_parquet)
from pyfortracc.vector_methods.split_mtd import split_mtd
from pyfortracc.vector_methods.merge_mtd import merge_mtd
from pyfortracc.vector_methods.incores_mtd import innercores_mtd
from pyfortracc.vector_methods.opticalflow_mtd import opticalflow_mtd
from pyfortracc.vector_methods.ellipse_mtd import ellipse_mtd
from .count_inside import count_inside
from .overlay import overlay_
from .spatial_class import continuous, merge, split, merge_split
from .expansion import expansion
from .trajectory import trajectory
from .edge_clusters import edge_clusters
from .validation import validation


def spatial_operations(name_lst, read_fnc, parallel=True):
    """ 
    Spatial Operations Module. This module is used to perform the spatial operations between two consecutive feature files.

    parameters
    ----------
    name_lst: dictionary
        dictionary with the parameters
    read_fnc: function
        function to read the data
    parallel: boolean
        True to run parallel, False to run in serial
    
    Returns
    -------
    None
    """
    print('Spatial Operations:')
    # Set default parameters
    name_lst = default_parameters(name_lst, read_fnc)
    # Check operational system
    name_lst, parallel = check_operational_system(name_lst, parallel)
    # Get feature files to be processed
    feat_path = name_lst['output_path'] + 'track/processing/features/'
    feat_files = get_feature_files(feat_path)
    #feat_files = get_previous_proccessed_files(name_lst, feat_files)
    # Set ouput to spatial operations
    output_path = name_lst['output_path'] + 'track/processing/spatial/'
    name_lst['output_spatial'] = output_path
    create_dirs(output_path)  # Create the directories
    # Get edges of the data, used to check if the cluster is on the edges
    left_edge, right_edge = get_edges(name_lst, feat_files, read_fnc)
    # Get loading bar
    loading_bar = get_loading_bar(feat_files)
    # Initialize schema
    schema = set_schema('spatial', name_lst)
    # Get number of prev_files to skip based on the number of prev_time
    prev_skip = name_lst['num_prev_skip']
    # Get geotransform
    geotrf, inv_geotrf = get_geotransform(name_lst)
    if parallel:
        # Set number of workers
        n_workers = set_nworkers(name_lst)
        with Pool(n_workers) as pool:
            for _ in pool.imap_unordered(spatial_operation,
                                         [(feat_time, feat_file,
                                           feat_files[feat_time - 1:
                                                      feat_time],
                                           feat_files[(feat_time - 1 +
                                                       prev_skip) - 1:
                                                      feat_time],
                                           name_lst, left_edge, right_edge,
                                           read_fnc, schema, False, geotrf)
                                          for feat_time, feat_file
                                          in enumerate(feat_files)]):
                loading_bar.update(1)
        pool.close()
    else:
        for feat_time, feat_file in enumerate(feat_files):
            spatial_operation((feat_time, feat_file,
                               feat_files[feat_time - 1: feat_time],
                               feat_files[(feat_time - 1 + prev_skip) - 1:
                                          feat_time],
                               name_lst, left_edge, right_edge, 
                               read_fnc, schema, False, geotrf))
            loading_bar.update(1)
    loading_bar.close()
    return


def spatial_operation(args):
    """
    Processes spatial operations for a given file, including computing cluster details, trajectories, and vector fields.

    Parameters
    ----------
    args : tuple
        A tuple containing the following elements:
        - time_ : int
            The current time index or frame number.
        - cur_file : str
            The path to the current Parquet file to be processed.
        - prv_file : str
            The path to the previous Parquet file used for comparison.
        - prv_files : list
            List of previous file paths for comparison.
        - nm_lst : dict
            Dictionary containing configuration settings and parameters, including:
            - 'output_spatial' : str
                The directory path where the output files will be saved.
            - 'thresholds' : list
                List of thresholds for spatial operations.
            - 'edges' : bool
                Flag indicating if edge detection should be performed.
            - 'opt_correction' : bool
                Flag indicating if optical flow correction should be applied.
            - 'operator' : str
                Operator used for optical flow correction.
            - 'opt_mtd' : str
                Method used for optical flow correction.
            - 'validation' : bool
                Flag indicating if validation should be performed.
        - l_edge : float
            The left edge boundary for edge detection.
        - r_edg : float
            The right edge boundary for edge detection.
        - read_fnc : function
            Function to read data from files.
        - schm : str
            Schema or format of the data.
        - fct : bool
            Flag indicating if the data comes from a forecast.

    Returns
    -------
    None
    """
    (time_, cur_file, prv_file, prv_files, nm_lst, \
    l_edge, r_edg, read_fnc, schm, fct, geotrf) = args
    
    # Get current_file name using pathlib
    current_file_name = pathlib.Path(cur_file).name
    output_file = nm_lst['output_spatial'] + current_file_name
    thresholds = nm_lst['thresholds']
    # Set necessary columns to spatial operations
    necs_cols = ['cluster_id','threshold_level', 'threshold', 'size',
                'geometry', 'centroid', 'file','array_y', 'array_x']
    # Read current file
    cur_frame = read_parquet(cur_file, necs_cols)
    spatial_df = set_outputdf(schm)
    spatial_col = list(spatial_df.columns)
    cur_frame = pd.concat([cur_frame, spatial_df])
    # Initialize cur_frame with all status as NEW
    cur_frame['status'] = 'NEW'
    cur_frame['trajectory'] = LineString().wkt
    cur_frame['vector_field'] = LineString().wkt
    # Convert to shapely geometry
    cur_frame['geometry'] = cur_frame['geometry'].apply(loads)
    # cur_frame['centroid'] = cur_frame['geometry'].centroid 
    cur_frame['centroid'] = cur_frame['geometry'].apply(lambda row: row.centroid) # check this later
    cur_frame = cur_frame.set_geometry('geometry')
    # check if time is 0 and start the process or if the current frame is empty
    if time_ == 0 or cur_frame.empty:
        # Only count inside clusters and update the current frame
        _, _, cnts = count_inside(cur_frame, 0)
        cur_frame.loc[cnts.index, 'inside_idx'] = cnts['index_inside']
        cur_frame.loc[cnts.index, 'inside_clusters'] = cnts['inside_len']
        # Check if the cluster is on the edges
        if nm_lst['edges']:
            cur_frame['board'] = False  # Set all clusters as False
            touch_lrg, touch_lowr = edge_clusters(cur_frame, l_edge, r_edg, nm_lst)
            cur_frame.loc[touch_lowr,'board'] = True
            cur_frame.loc[touch_lowr,'board_idx'] = touch_lrg
        cur_frame['trajectory'] = cur_frame['trajectory'].astype(str)
        if nm_lst['validation']:
            cur_frame['method'] = 'noc'
            cur_frame['far'] = 1
        write_parquet(cur_frame[spatial_col], output_file)
        return
    # Get previous file based on current file and search in previous files
    prv_file = get_previous_file(cur_file, prv_file, prv_files, nm_lst)
    if prv_file is None:
        # Only count inside clusters and update the current frame
        _, _, cnts = count_inside(cur_frame, 0)
        cur_frame.loc[cnts.index, 'inside_idx'] = cnts['index_inside']
        # Check if the cluster is on the edges
        if nm_lst['edges']:
            cur_frame['board'] = False  # Set all clusters as False
            touch_lrg, touch_lowr = edge_clusters(cur_frame, l_edge, r_edg, nm_lst)
            cur_frame.loc[touch_lowr,'board'] = True
            cur_frame.loc[touch_lowr,'board_idx'] = touch_lrg
        cur_frame['trajectory'] = cur_frame['trajectory'].astype(str)
        write_parquet(cur_frame[spatial_col], output_file)
        return
    # Read previous file
    prv_frame = read_parquet(prv_file, necs_cols)
    prv_frame['geometry'] = prv_frame['geometry'].apply(loads)
    # prv_frame['centroid'] = prv_frame['centroid'].apply(loads)
    prv_frame['centroid'] = prv_frame['geometry'].apply(lambda row: row.centroid) # check this later
    prv_frame = prv_frame.set_geometry('geometry')
    # Drop cindex if the frame come from forecast
    if fct:
        prv_frame.reset_index(drop=True, inplace=True)
    # Compute the overlays for each threshold
    # Loop over reversed (inside to outise) thresholds to perform spatial operations
    for threshold in thresholds[::-1]:
        operation_df = operations(cur_frame, prv_frame, threshold, 
                                  l_edge, r_edg, nm_lst)
        # Update current frame based on index
        cur_frame.loc[operation_df.index] = operation_df
    # Optical flow method: Read instructions in optical_flow.py
    # This method is used outside the thresholds loop because not necessary
    if nm_lst['opt_correction']:
        opt_idx, u_, v_, v_field = opticalflow_mtd(cur_frame,
                                                   prv_frame,
                                                   nm_lst,
                                                   geotrf)
        # Update current frame based on index
        cur_frame.loc[opt_idx,'u_opt'] = u_
        cur_frame.loc[opt_idx,'v_opt'] = v_
        cur_frame.loc[opt_idx,'vector_field'] = v_field
        cur_frame['vector_field'] = cur_frame['vector_field'].astype(str)
    # Save the result
    cur_frame['trajectory'] = cur_frame['trajectory'].astype(str)
    # Calculate best method if validation is True
    if nm_lst['validation']:
        if time_ >= 1: # Validate only after the second frame
            # Copy columns u_ and v_ to u_noc and v_noc
            cur_frame['u_noc'] = cur_frame['u_']
            cur_frame['v_noc'] = cur_frame['v_']
            # Call validation function
            cur_frame = validation(cur_frame, prv_frame, nm_lst)
            # Fill method equals None to noc
            cur_frame['method'] = cur_frame['method'].fillna('noc')
            cur_frame['far'] = cur_frame['far'].fillna(1)
    # Save the result
    write_parquet(cur_frame[spatial_col], output_file)
    return


def operations(cur_frme, prv_frme, threshold, l_edge, r_edg, nm_lst):
    """ 
    Perform spatial operations between two dataframes

    Parameters
    -------
    cur_frme : DataFrame
        Current time dataframe
    prv_frme : DataFrame 
        Previous time dataframe
    threshold : int
        Threshold to be processed
    nm_lst : dict 
        Name list with the parameters
    
    Returns
    cur_frme : DataFrame
        Current time dataframe with spatial operations
    """
    # First spatial operations is count inside clusters
    # For this function is necessary have all thresholds
    # in cur_frme.
    # Get threshold level
    thd_lvl = nm_lst['thresholds'].index(threshold)
    cur_thd_idx, ins_thd_idx, cnts_ = count_inside(cur_frme, thd_lvl)
    if len(cur_thd_idx) > 0:
        cur_frme.loc[cnts_.index, 'inside_idx'] = cnts_['index_inside']
        cur_frme.loc[cnts_.index, 'inside_clusters'] = cnts_['inside_len']
        # Create insd_frme to be used in other spatial operations
        insd_frme = cur_frme.loc[ins_thd_idx]
    # Select only clusters with same threshold
    cur_frme = cur_frme.loc[cur_frme['threshold'] == threshold]
    prv_frme = prv_frme.loc[prv_frme['threshold'] == threshold]
    # Check if frames are empty
    if cur_frme.empty or prv_frme.empty:
        return cur_frme
    # Second spatial operation is overlay
    # For this function is necessary have both frames
    # in the same threshold, and pass the minimum overlap
    overlays = overlay_(cur_frme, prv_frme, nm_lst['min_overlap'])
    if overlays.empty:
        # Check if the cluster is on the edges
        if nm_lst['edges'] and nm_lst['thresholds'][0] == threshold:
            touch_lrg, touch_lowr = edge_clusters(cur_frme, l_edge, r_edg, nm_lst)
            cur_frme.loc[touch_lowr,'board'] = True
            cur_frme.loc[touch_lowr,'board_idx'] = touch_lrg
        return cur_frme
    # Get overlay index and overlap from overlays
    ovrp_indx = overlays['index_1'].values
    ovrp_area = overlays['overlap'].values
    # Update current frame based on index
    cur_frme.loc[ovrp_indx,'overlap'] = ovrp_area
    # Get index based on overlays
    cont_indx, cont_prv_indx = continuous(overlays)
    mergs_idx, mergs_prv_idx, merge_frame = merge(overlays)
    splits_idx, split_prev_idx, nw_splt_idx, nw_splt_prv_idx = split(overlays) 

    # Classify merge splits index
    cur_frme.loc[nw_splt_idx,'split_pr_idx'] =  nw_splt_prv_idx # Previous split
    cur_frme.loc[mergs_idx,'merge_idx'] =  merge_frame['merge_ids'].values # Previous merge
    cur_frme.loc[splits_idx,'split_idx'] =  split_prev_idx # Current split

    # Add past_idx, merge_idx and split_pr_idx to current frame
    cur_frme.loc[cont_indx, 'past_idx'] = cont_prv_indx # Continuous
    cur_frme.loc[mergs_idx,'past_idx'] =  mergs_prv_idx # Merge
    cur_frme.loc[splits_idx,'past_idx'] =  split_prev_idx # Split
    
    # Update status, prev_idx, merge_idx, split_idx
    cur_frme.loc[cont_indx,'status'] =  'CON'
    cur_frme.loc[mergs_idx,'status'] =  'MRG'
    cur_frme.loc[splits_idx,'status'] =  'SPL'
    cur_frme.loc[nw_splt_idx,'status'] =  'NEW/SPL'    
    
    # Check if there is any intersection between mergs and splits
    # If there is any intersection, the clusters are considered
    mrg_spl_idx, prev_past_idx = merge_split(mergs_idx, splits_idx,
                                 cur_frme, prv_frme)
    cur_frme.loc[mrg_spl_idx,'status'] =  'MRG/SPL'
    cur_frme.loc[mrg_spl_idx,'past_idx'] =  prev_past_idx
    
    # Mount the trajectory LineString, distance and direction
    # Select non null prev_idx is concat into a single array
    # This is necessary because the trajectory function only
    # works with non null prev_idx at the current frame
    cur_non_null_idx = np.concatenate((cont_indx, mergs_idx, splits_idx))
    if len(cur_non_null_idx) > 0:
        cur_trj = cur_frme.loc[cur_non_null_idx]
        prev_trj = prv_frme.loc[cur_trj['past_idx'].values]
        lines, u_, v_ = trajectory(cur_trj, prev_trj)
        cur_frme.loc[cur_non_null_idx,'trajectory'] = lines
        cur_frme.loc[cur_non_null_idx,'u_'] = u_
        cur_frme.loc[cur_non_null_idx,'v_'] = v_
        # calling expansion function with current and previous clusters and delta_time
        exp_norm = expansion(cur_trj, prev_trj, prv_frme, 
                             nm_lst['delta_time'], nm_lst['mrg_expansion'])
        cur_frme.loc[cur_non_null_idx,'expansion'] = exp_norm
    # Vector methods additons
    # Split method: Read instructions in split_mtd.py
    if nm_lst['spl_correction'] and len(nw_splt_idx) > 0:
        cur_spl = cur_frme.loc[nw_splt_idx]
        prv_spl = prv_frme.loc[cur_spl['split_pr_idx'].values]
        lines, u_, v_ = split_mtd(cur_spl, prv_spl, nw_splt_idx)
        cur_frme.loc[nw_splt_idx,'trajectory'] = lines
        cur_frme.loc[nw_splt_idx,'u_spl'] = u_
        cur_frme.loc[nw_splt_idx,'v_spl'] = v_
    # Merge method: Read instructions in merge_mtd.py
    if nm_lst['mrg_correction'] and len(mergs_idx) > 0:
        cur_mrg = cur_frme.loc[mergs_idx]
        prev_mrgs = cur_frme.loc[mergs_idx,'merge_idx']
        perv_mrg_idx = prev_mrgs.explode().values
        prv_mrg = prv_frme.loc[perv_mrg_idx]
        u_, v_= merge_mtd(cur_mrg, prv_mrg, mergs_idx, prev_mrgs)
        cur_frme.loc[mergs_idx,'u_mrg'] = u_
        cur_frme.loc[mergs_idx,'v_mrg'] = v_
    # Inner cores method: Read instructions in incores_mtd.py
    if nm_lst['inc_correction'] and len(np.intersect1d(cur_thd_idx,
                                                    cur_non_null_idx)) > 0:
        # insd_idx is a index list of current threshold clusters have inside
        # cluster and non null prev_idx
        insd_idx = np.intersect1d(cur_thd_idx, cur_non_null_idx)
        cur_base = cur_frme.loc[insd_idx].dropna(subset=['inside_idx'])
        insd_idx = cur_base.index.values
        if len(cur_base) > 0:
            cur_inner_idx = cur_base['inside_idx'].values
            cur_insd_idx = cur_base['inside_idx'].explode().values
            # Select only inside clusters, insd_frame comming from count_inside
            cur_inner = insd_frme.loc[cur_insd_idx]
            u_, v_= innercores_mtd(cur_base, cur_inner, insd_idx, cur_inner_idx)
            cur_frme.loc[insd_idx,'u_inc'] = u_
            cur_frme.loc[insd_idx,'v_inc'] = v_
    # Ellipse method: Read instructions in ellipse_mtd.py
    if nm_lst['elp_correction'] and len(cur_non_null_idx) > 0:
        cur_ell = cur_frme.loc[cur_non_null_idx]
        prev_ell = prv_frme.loc[cur_ell['past_idx'].values]
        u_, v_ = ellipse_mtd(cur_ell, prev_ell)
        cur_frme.loc[cur_non_null_idx,'u_elp'] = u_
        cur_frme.loc[cur_non_null_idx,'v_elp'] = v_
    # Check if the cluster is on the edges
    if nm_lst['edges'] and nm_lst['thresholds'][0] == threshold:
        cur_frme['board'] = False
        touch_lrg, touch_lowr = edge_clusters(cur_frme, l_edge, r_edg, nm_lst)
        cur_frme.loc[touch_lowr,'board'] = True
        cur_frme.loc[touch_lowr,'board_idx'] = touch_lrg
    return cur_frme
