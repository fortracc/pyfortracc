import pandas as pd
import numpy as np
import warnings
from multiprocessing import Pool
from pyfortracc.default_parameters import default_parameters
from .clustering import clustering
from .statistics import geo_statistics
from pyfortracc.utilities.utils import (get_input_files, set_operator,
                                        create_dirs, write_parquet, set_schema,
                                        set_outputdf, set_nworkers,
                                        get_loading_bar, get_filestamp)
from pyfortracc.utilities.conversions import dbz2mm6m3, mm6m32dbz
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)


def features_extraction(name_lst, read_fnc, parallel=True):
    """ 
    Features Extraction Module. This module is used to extract the features from the data.

    parameters:
    ----------
    name_lst: dictionary
        dictionary with the parameters
    read_fnc: function
        function to read the data
    parallel: boolean
        True to run parallel, False to run in serial
    """
    print('Features Extraction:')
    # Set default parameters
    name_lst = default_parameters(name_lst)
    # Get the input files and filestamp
    files = get_input_files(name_lst['input_path'])
    # Set the operator used to thresholding segmentation
    operator = set_operator(name_lst['operator'])
    # Get loading bar
    loading_bar = get_loading_bar(files)
    # Create output directories and update output_path in name_lst
    output_path = name_lst['output_path'] + 'track/processing/features/'
    name_lst['output_features'] = output_path
    # Create the directories
    create_dirs(output_path)
    # Initialize schema of the output dataframe
    schema = set_schema('features', name_lst)
    if parallel:
        # Set number of workers
        n_workers = set_nworkers(name_lst)
        with Pool(n_workers) as pool:
            for _ in pool.imap_unordered(extract_features,
                                        [(file, name_lst, operator,
                                        read_fnc, schema)
                                        for _, file in enumerate(files)]):
                loading_bar.update(1)
        pool.close()
    else:
        for _, file in enumerate(files):
            extract_features((file, name_lst, operator,
                            read_fnc, schema))
            loading_bar.update(1)
    loading_bar.close()


def extract_features(args):
    """
    Calculate the features for a single file

    args parameters:
    ----------
    file: string
        path to the file
    name_list: dictionary
        dictionary with the parameters
    operator: function
        function to be used to thresholding segmentation
    read_func: function
        function to read the data
    """
    file, name_list, operator, read_func, schema = args
    # Initialize the features dataframe
    output_df = set_outputdf(schema)
    # Get the timestamp from the file
    tstamp = get_filestamp(name_list['timestamp_pattern'], file)
    fpattern = '%Y%m%d_%H%M'  # File pattern
    output_path = name_list['output_features']
    min_size = name_list['min_cluster_size']
    cluster_mtd = name_list['cluster_method']
    feature_file = output_path + '{}.parquet'.format(tstamp.strftime(fpattern))
    # Read the data from the file using the read_func
    try:
        data = read_func(file)
    except Exception as e:
        print('Error reading file: {}'.format(file), e)
        write_parquet(output_df, feature_file)
        return
    # Start processing clustering and geo_statistics
    for thld_lvl, threshold in enumerate(name_list['thresholds']):
        # Calculate the clusters
        clusters, labels = clustering(cluster_mtd, data, operator,
                                    threshold, min_size[thld_lvl],
                                    name_list['eps'])
        # Calculate the geo_statistics
        clu_stats = geo_statistics(clusters, labels, data, name_list)
        clu_stats['threshold'] = threshold
        clu_stats['threshold_level'] = thld_lvl
        output_df = pd.concat([output_df, clu_stats], axis=0)
    # If mean_dbz is True, calculate the mean_dbz for dbz values
    if 'mean_dbz' in name_list.keys() and name_list['mean_dbz']:
        mm6m3_values = output_df['array_values'].apply(dbz2mm6m3)
        mean_mm6m3_values = mm6m3_values.apply(np.nanmean)
        std_mm6m3_values = mm6m3_values.apply(np.nanstd)
        # Convert back to dbz and store in the output_df
        output_df['mean'] = mean_mm6m3_values.apply(mm6m32dbz)
        output_df['std'] = std_mm6m3_values.apply(mm6m32dbz)
    # Save the features
    output_df['file'] = file
    output_df['timestamp'] = tstamp
    output_df.reset_index(inplace=True, drop=True)
    write_parquet(output_df, feature_file)
    return