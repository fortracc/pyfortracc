import glob
import pathlib
import duckdb
import pandas as pd
import multiprocessing as mp
from pyfortracc.utilities.utils import set_nworkers, get_loading_bar, check_operational_system
from pyfortracc import default_parameters

def compute_duration(namelist, parallel=True):
    """ 
    This function calculates the duration of the clusters using DuckDB.
    
    Parameters
    ----------
    namelist : dict
        Dictionary with the parameters to be used.
    parallel : bool, optional
        If True, the function will run in parallel. Default is True.
        
    Returns
    -------
    None
    """
     # Check operational system
    namelist, parallel = check_operational_system(namelist, parallel)
    # Get all track files
    files = sorted(glob.glob(namelist['output_path'] + 'track/trackingtable/' + '*.parquet'))
    if len(files) == 0:
        print('No track files found at ' + namelist['output_path'] + 'track/trackingtable/')
        return
    # Get timestamps from files
    tstamps = [pd.to_datetime(pathlib.Path(file).name, format='%Y%m%d_%H%M.parquet') for file in files]
    namelist = default_parameters(namelist)
    n_workers = set_nworkers(namelist)
    global df # Make df global to be used in update_parquet
    global con
    if len(namelist['thresholds']) > 1:
        proc_col = 'iuid'
        proc_col2 = 'uid'
    else:
        proc_col = 'uid'
        proc_col2 = 'uid'
    # Using DuckDB to read the parquet files and process the data
    con = duckdb.connect(database=':memory:') 
    con.execute('PRAGMA enable_progress_bar;')
    con.execute(f"SET threads = {n_workers}")
    # Set the query to be executed
    # This query will group the data by the column proc_col and
    #  calculate the duration of each cluster based on the timestamps
    query = f"""
        SELECT 
            COALESCE({proc_col}, {proc_col2}) AS {proc_col}, 
            MIN(timestamp) AS first_timestamp, 
            MAX(timestamp) AS last_timestamp,
            DATEDIFF('minute', MIN(timestamp), MAX(timestamp)) AS duration
        FROM 
            read_parquet('{namelist['output_path']}track/trackingtable/*.parquet')
        WHERE 
            {proc_col} IS NOT NULL OR {proc_col2} IS NOT NULL
        GROUP BY 
            COALESCE({proc_col}, {proc_col2})
        HAVING 
            DATEDIFF('minute', MIN(timestamp), MAX(timestamp)) > 0
    """
    con.execute("CREATE TABLE df AS " + query)
    con.execute('PRAGMA disable_progress_bar;')
    print('Computing duration:')
    # Loop over files
    load_bar = get_loading_bar(files)
    if parallel:
        with mp.Pool(n_workers) as pool:
            for _ in pool.imap_unordered(update_parquet, [(tstamps[tt], files[tt]) for tt in range(len(tstamps))]):
                load_bar.update(1)
    else:
        for tt in range(len(tstamps)):
            update_parquet((tstamps[tt], files[tt]))
            load_bar.update(1)
    load_bar.close()
    return

def update_parquet(args):
    """
    Update the duration information in a Parquet file based on cluster data.
    
    Parameters
    ----------
    args : tuple
        A tuple containing:
        - timestamp_ : pd.Timestamp
            The timestamp used to filter clusters within a specific time range.
        - file_path : str
            The file path to the Parquet file that needs to be updated.

    Returns
    -------
    None
    """
    timestamp_, file_path = args
    try:
        query = f"""
        SELECT *
        FROM df
        WHERE first_timestamp <= '{timestamp_}' AND last_timestamp >= '{timestamp_}'
        """
        clusters = con.execute(query).fetch_df()
        if clusters.empty:
            return
        # Read parquet file
        feature_df = pd.read_parquet(file_path)
        # Where iuid is null, set iuid to uid
        if 'iuid' in feature_df.columns:
            update = feature_df['iuid'].fillna(feature_df['uid']).reset_index()
            update.set_index('iuid', inplace=True)
            clusters = clusters.reset_index()
            clusters.set_index('iuid', inplace=True)
        else:
            update = feature_df['uid'].reset_index()
            update.set_index('uid', inplace=True)
            clusters = clusters.reset_index()
            clusters.set_index('uid', inplace=True)
        # Update duration, start_time, and end_time
        update['duration'] = clusters['duration']
        update['start_time'] = clusters['first_timestamp']
        update['end_time'] = clusters['last_timestamp']
        update.set_index('cindex', inplace=True)
        feature_df['duration'] = update['duration']
        feature_df['duration'] = feature_df['duration'].fillna(0)
        feature_df['duration'] = feature_df['duration'].astype(int)
        # This part is used to compute lifetime using duration module, uncomment if needed
        # Calculate lifetime based on timestamp and end_time
        # feature_df['lifetime'] = feature_df['timestamp'] - update['start_time']
        # feature_df['lifetime'] = feature_df['lifetime'].dt.total_seconds() / 60
        # feature_df['lifetime'] = feature_df['lifetime'].fillna(0)
        # feature_df['lifetime'] = feature_df['lifetime'].astype(int)
        # # This part get lifetime of split clusters and add to splited clusters
        # if len(feature_df.loc[feature_df['split_cur_idx'].notnull()]) > 0:
        #     feature_df.reset_index(inplace=True)
        #     split_frs = feature_df.loc[feature_df['split_cur_idx'].notnull()]
        #     split_idx = split_frs['split_cur_idx'].values.astype(int)
        #     lifetimes = feature_df.loc[split_idx]['lifetime']
        #     feature_df.loc[split_frs.index, 'lifetime'] = lifetimes.values
        #     feature_df.set_index('cindex', inplace=True)
        # Add genesis column to indicate the start and end of the cluster
        feature_df.loc[feature_df['timestamp'] == update['start_time'], 'genesis'] = 1
        feature_df.loc[feature_df['timestamp'] == update['end_time'], 'genesis'] = -1
        feature_df['genesis'] = feature_df['genesis'].fillna(0)
        feature_df['genesis'] = feature_df['genesis'].astype(int)
        del clusters
        feature_df.to_parquet(file_path)
    except Exception as e:
        print(f'Error in file {file_path}: {e}')
    return
