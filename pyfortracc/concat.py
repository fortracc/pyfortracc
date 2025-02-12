import glob
import numpy as np
import os
import shutil
import pandas as pd
import pyarrow as pa
import pathlib
from pyarrow.lib import Schema
from multiprocessing import Pool
from pyfortracc.utilities.utils import get_loading_bar, set_nworkers, check_operational_system
from pyfortracc.default_parameters import default_parameters



def concat(name_list, mode='track', clean=True, parallel=True):
    ''' 
    This function concatenates the results of the FortraCC algorithm
    into a single parquet file. The results are stored in the output_path/
    trackingtable if the processing is track or directory.
    The parquet file contains the following columns:

    Parameters
    -------
    name_list : dict
        Dictionary with the parameters to be used.
    mode : str
        Mode of the processing. Default is 'track'.
    clean : bool
        If True, the processing directory is removed after concatenation.
        Default is True.

    Returns
    -------
    None
    '''
    print('Concatenating:')
    proc_path = name_list['output_path'] + mode + '/processing/'
    # Set default parameters
    name_list = default_parameters(name_list)
    # Check operational system
    name_list, parallel = check_operational_system(name_list, parallel)
    # Set name of the output file
    if 'concat_path' not in name_list:
        name_list['concat_path'] = name_list['output_path']
    if mode == 'track':
        output_path = name_list['concat_path'] + 'track/trackingtable/'
    elif mode == 'forecast':
        output_path = name_list['concat_path'] + 'forecast/forecastable/'
    else:
        raise ValueError('Invalid mode')
    # Check if proc_path exists
    if not os.path.exists(proc_path) or os.path.isfile(output_path):
        print('No files to concatenate, the trackingtable already exists')
        print(output_path)
        return
    # Feature files
    fet_files = sorted(glob.glob(proc_path + 'features/*.parquet'))
    spt_files = sorted(glob.glob(proc_path + 'spatial/*.parquet'))
    lnk_files = sorted(glob.glob(proc_path + 'linked/*.parquet'))
    # Set default columns
    if name_list['default_columns']:
        default_cols = default_columns(name_list)
        if name_list['validation_scores']:
            last_spt = pd.read_parquet(spt_files[-1])
            concat_cols = last_spt.columns
            for col in concat_cols:
                if 'hit' in col or 'false-alarm' in col:
                    default_cols.append(col)
    # Create output directory
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    # Get schema from the last file        
    schema = read_files((fet_files[-1], spt_files[-1], lnk_files[-1], 
                        default_cols, output_path, None, False))
    # Loading bar
    loading_bar = get_loading_bar(fet_files)
    if parallel:
        # Set number of workers
        n_workers = set_nworkers(name_list)
        with Pool(n_workers) as pool:
            for _ in pool.imap_unordered(read_files,
                                        [(fet_file, spt_file, lnk_file, 
                                            default_cols, output_path, schema, clean)
                                        for fet_file, spt_file, lnk_file in zip(fet_files, spt_files, lnk_files)]):
                loading_bar.update(1)
        pool.close()
    else:
        for fet_file, spt_file, lnk_file in zip(fet_files, spt_files, lnk_files):
            read_files((fet_file, spt_file, lnk_file, default_cols, 
                        output_path, schema, clean))
            loading_bar.update(1)
    loading_bar.close()           
    # Clean the processing directory
    if clean:
        shutil.rmtree(proc_path)
        
def read_files(args):
    ''' 
    This function reads multiple Parquet files, processes the data by dropping unnecessary columns, and concatenates them into a single DataFrame. 
    The resulting DataFrame is then filtered based on a set of default columns, indexed, and cleaned of duplicate columns.

    Parameters
    -------
    - `fet_file` : str
        Path to the feature file.
    - `spat_file` : str
        Path to the spatial file.
    - `link_file` : str
        Path to the link file.
    - `default_columns` : list
        List of columns to retain after concatenation.
    - `output_path` : str
        Directory path to save the processed Parquet file.
    - `schema` : Schema or None
        Schema for saving the output Parquet file. If None, the schema is inferred from the DataFrame.
    - `clean` : bool
        Flag to indicate whether to clean temporary files after saving.

    Returns
    -------
    None
    '''
    fet_file, spat_file, link_file, default_columns, output_path, schema, clean = args
    # Read feature files
    feat_df = pd.read_parquet(fet_file)
    spat_df = pd.read_parquet(spat_file)
    # Drop column threshold_level and trajectory from spat_df
    spat_df = spat_df.drop(columns=['threshold_level', 'trajectory'])
    link_df = pd.read_parquet(link_file)
    # Drop column threshold_level from link_df
    link_df = link_df.drop(columns=['threshold_level'])
    concat_df = pd.concat([feat_df, spat_df, link_df], axis=1)
    # Select columns
    concat_df = concat_df[default_columns]
    # Set index
    concat_df.set_index('cindex', inplace=True)
    # Drop duplicates columns
    concat_df = concat_df.loc[:,~concat_df.columns.duplicated()]
    # Check if schema is None
    if schema is None:
        return Schema.from_pandas(concat_df)
    # Get the name of file
    file_name = pathlib.Path(fet_file).name
    file_name = output_path + file_name
    # Check if file exist and remove it
    if os.path.exists(file_name):
        os.remove(file_name)
    # Save the parquet file
    save_parquet(concat_df, file_name, schema,
                clean=False, del_files=[fet_file, spat_file, link_file])
    

def save_parquet(concat_df, output_file, schema, clean=False, del_files=[]):
    ''' 
    This function saves a DataFrame to a Parquet file with specified schema and compression. 
    It also provides an option to delete input files after saving.

    Parameters
    -------
    - `concat_df` : pd.DataFrame
        The DataFrame to be saved as a Parquet file.
    - `output_file` : str
        Path where the output Parquet file will be saved.
    - `schema` : pyarrow.Schema
        Schema to enforce on the DataFrame before saving.
    - `clean` : bool, optional
        If True, deletes the original input files specified in `del_files` after saving. Default is False.
    - `del_files` : list, optional
        List of file paths to be deleted if `clean` is set to True. Default is an empty list.

    Returns
    -------
    None
    '''
    # table = pa.Table.from_pandas(concat_df, schema=schema)
    # df_converted = table.to_pandas()
    concat_df.to_parquet(output_file, engine='pyarrow', compression='gzip',
                            )
    if clean:
        for file in del_files:
            os.remove(file)

def default_columns(name_list=None):
    '''
    This function generates and returns a list of default columns based on the provided configuration in `name_list`.
    It dynamically adjusts the columns based on the presence of specific keys and their corresponding values in `name_list`.

    Parameters
    -------
    - `name_list` : dict 
        A dictionary containing configuration flags that determine which additional columns should be included. 
        The keys include 'thresholds', 'validation', 'validation_scores', 'spl_correction', 'mrg_correction', 
        and 'opt_correction', which control whether specific sets of columns should be added.

    Returns
    -------
    - `columns` : list
        A list of column names to be saved, which may include default columns and additional ones based on 
    '''
    columns = ['timestamp',
                'cindex',
                'uid',
                'threshold_level',
                'threshold',
                'status',
                'size',
                'lifetime',
                'expansion',
                'min',
                'mean',
                'max',
                'std',
                'u_',
                'v_',
                'inside_clusters',
                'board',
                'cluster_id',
                'file',
                'array_values',
                'array_y',
                'array_x',
                'vector_field',
                'trajectory',
                'geometry',
                'cluster_id',
                'past_idx',
                'merge_idx',
                'split_pr_idx']
    
    if len(name_list['thresholds']) > 1:
        # columns = columns + ['iuid']
        # Get position of uid column and add iuid after it
        uid_pos = columns.index('uid')
        columns = columns[:uid_pos + 1] + ['iuid'] + columns[uid_pos + 1:]
    if name_list['validation']:
        columns = columns + ['far', 'method']
    if name_list['validation_scores']:
        columns = columns + ['u_noc','v_noc',
                            'far_', 'hit_', 'false-alarm_']
    if name_list['spl_correction']:
        columns = columns + ['u_spl'] + ['v_spl']
        if name_list['validation_scores']:
            columns = columns + ['far_spl','hit_spl', 'false-alarm_spl']
    if name_list['mrg_correction']:
        columns = columns + ['u_mrg'] + ['v_mrg']
        if name_list['validation_scores']:
            columns = columns + ['far_mrg','hit_mrg', 'false-alarm_mrg']
    if name_list['validation_scores']:
        columns = columns + ['u_inc'] + ['v_inc']
        if name_list['validation_scores']:
            columns = columns + ['far_inc', 'hit_inc', 'false-alarm_inc']
    if name_list['opt_correction']:
        columns = columns + ['u_opt'] + ['v_opt']      
        if name_list['validation_scores']:
            columns = columns + ['far_opt', 'hit_opt', 'false-alarm_opt']
    if name_list['elp_correction']:
        columns = columns + ['u_elp'] + ['v_elp']
        if name_list['validation_scores']:
            columns = columns + ['far_elp', 'hit_elp', 'false-alarm_elp']
    if name_list['calc_dir']:
        columns = columns + ['dir']
    if name_list['calc_speed']:
        columns = columns + ['speed']
    if name_list['prv_uid']:
        columns = columns + ['prv_mrg_uids', 'prv_mrg_iuids', 
                             'prv_spl_uid', 'prv_spl_iuid']
    return columns
