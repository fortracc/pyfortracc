import glob
import os
import platform
import sys
import psutil
import numpy as np
import pandas as pd
import geopandas as gpd
import pathlib
import multiprocessing as mp
import inspect
import xarray as xr
from tqdm import tqdm
from datetime import datetime, timedelta
from shapely.geometry import LineString


def get_input_files(input_path):
    """
    Retrieve a list of files from the specified input directory.

    This function scans the provided directory path and collects all files into a list. 
    It supports recursive directory traversal, ensuring that files in subdirectories 
    are also included. If no files are found, the function prints a message and exits the program.

    Parameters
    ----------
    input_path : str
        The path to the directory from which files will be retrieved. This can include 
        subdirectories, and the function will search recursively.

    Returns
    -------
    list of str
        A sorted list of file paths found within the specified directory and its subdirectories.

    Raises
    ------
    SystemExit
        If no files are found in the given directory path, the function prints an error message 
        and exits the program.
    """
    files_list = sorted(glob.glob(input_path + '**/*', recursive=True))
    files_list = [file for file in files_list if os.path.isfile(file)]
    if not files_list:
        print('Input path is empty', input_path)
        sys.exit()
    return files_list

def get_files_interval(files_list, files_pattern, name_list):
    """Filter files based on a specified time interval.
    This function filters a list of files based on a specified time interval defined by
    `track_start` and `track_end` in the `name_list`. It uses the provided `files_pattern`
    to extract timestamps from the file names and retains only those files whose timestamps
    fall within the specified interval.
    Parameters
    ----------
    - `files_list` : list
        The list of files to filter.
    - `files_pattern` : str
        The pattern to use for extracting timestamps from file names.
    - `name_list` : dict
        The dictionary containing the time interval information.
    Returns
    -------
    list
        A filtered list of files that fall within the specified time interval.
    """

    # For track files, use timestamp_pattern and for forecast use files_pattern
    if name_list['track_start'] is not None or name_list['track_end'] is not None:
        # Get file timestamps from the file names
        track_stamps = [get_featstamp(file) for file in files_list]
        track_start = None
        track_end = None

        if name_list['track_start'] is not None:
            # Convert track_start to datetime object
            track_start = datetime.strptime(name_list['track_start'], '%Y-%m-%d %H:%M:%S')

        if name_list['track_end'] is not None:
            # Convert track_end to datetime object
            track_end = datetime.strptime(name_list['track_end'], '%Y-%m-%d %H:%M:%S')
        
        # Check if track_start and track_end are defined
        if track_start is None:
            track_start = datetime.min  # Default to min datetime if track_start is not provided
        if track_end is None:
            track_end = datetime.max  # Default to max datetime if track_end is not provided

        # filter files based on the track start and end
        files_list = [
            file for file, stamp in zip(files_list, track_stamps)
            if track_start <= stamp <= track_end
        ]

    # For forecast files use files_pattern
    if name_list['forecast_time'] is not None:
        # Get file timestamps from the file names
        forecast_stamps = [datetime.strptime(pathlib.Path(file).name, files_pattern) for file in files_list]
        # Convert forecast_time to datetime object
        forecast_time = datetime.strptime(name_list['forecast_time'], '%Y-%m-%d %H:%M:%S')
        # Get forecast window is a number of files before the forecast time
        num_obs_files = name_list['observation_window']
        # Get the forecast window files based in position of forecast_time and num_obs files, exemple: get last 5 files before forecast_time in files_list
        # Not use any temporal argument
        files_list = [
            file for file, stamp in zip(files_list, forecast_stamps)
            if stamp <= forecast_time
        ]
        # Get the last num_obs_files files before the forecast time
        files_list = files_list[-num_obs_files:]

    return files_list

def get_feature_files(features_path, name_list=None):
    """
    Retrieve a list of `.parquet` files from the specified directory.

    This function scans the given directory for files with a `.parquet` extension and 
    returns them as a sorted list. If no `.parquet` files are found, the function prints 
    an error message and exits the program.

    Parameters
    ----------
    features_path : str
        The path to the directory from which `.parquet` files will be retrieved.

    Returns
    -------
    files_list : list of str
        A sorted list of file paths that have the `.parquet` extension found within the 
        specified directory.

    Raises
    ------
    SystemExit
        If no `.parquet` files are found in the given directory path, the function prints 
        an error message and exits the program.
    """
    files_list = sorted(glob.glob(features_path +'/*.parquet'))
    if not files_list:
        print('Input path is empty', features_path)
        sys.exit()

    if name_list is not None:
        file_pattern = '%Y%m%d_%H%M.parquet'
        files_list = get_files_interval(files_list, file_pattern, name_list)


    if len(files_list) == 0:
        print('No feature files found in the specified path:', features_path)
        sys.exit()
    return files_list

def get_previous_proccessed_files(name_list, feat_files):
    """
    Retrieve the list of feature files that have not been processed yet.

    This function determines the module from which it was called and uses this information 
    to locate previously processed files in a specific directory. It then returns the list 
    of feature files that are pending processing by removing those that have already been 
    processed.

    Parameters
    ----------
    name_list : dict
        A dictionary containing configuration parameters including paths for previous 
        processing output directories.
    feat_files : list of str
        A list of file paths to be processed.

    Returns
    -------
    feat_files : list of str
        A list of file paths from `feat_files` that have not yet been processed, based on 
        the files found in the respective previous processing directory.
    """
    # Get current module name comming from python function using inspect
    module_name = inspect.stack()[1][3]
    if module_name == 'feature_extraction':
        prev_files = sorted(glob.glob(name_list['output_path'] + \
                                    'track/processing/features/*.parquet'))
    elif module_name == 'spatial_operations':
        prev_files = sorted(glob.glob(name_list['output_path'] + \
                                    'track/processing/spatial/*.parquet'))
    elif module_name == 'cluster_linking':
        prev_files = sorted(glob.glob(name_list['output_path'] + \
                                    'track/processing/linked/*.parquet'))
    else:
        return feat_files
    if len(prev_files) == 0:
        return feat_files
    # Remove the files by difference
    size_prev = len(prev_files) - int(name_list['n_jobs'])
    # Remove first feat_files according the size_prev
    feat_files = feat_files[size_prev:]
    return feat_files
    

def get_parquets(name_list):
    """
    Retrieve and organize a list of Parquet files for processing.

    This function searches for Parquet files within the specified output path that match 
    the pattern of tracking table files. It then organizes these files into a DataFrame 
    with additional metadata, including timestamps and modes extracted from the file paths.

    Parameters
    ----------
    name_list : dict
        A dictionary containing configuration parameters including the `output_path` which
        specifies the base directory where the Parquet files are located.

    Returns
    -------
    files_df : pd.DataFrame
        A DataFrame containing the following columns:
        - 'file': The path to the Parquet file.
        - 'timestamp': The timestamp extracted from the file path.
        - 'mode': The mode of the file, extracted from the directory structure.
        
        The DataFrame is indexed by 'timestamp' and sorted in ascending order based on 
        this index.
    """
    files_list = sorted(glob.glob(name_list['output_path'] + '**/trackingtable/*.parquet',
                                recursive=True))
    files_df = pd.DataFrame(files_list, columns=['file'])
    files_df['timestamp'] = files_df['file'].apply(get_featstamp)
    files_df['mode'] = files_df['file'].apply(lambda x: pathlib.Path(x).parts[-3])
    files_df = files_df.set_index('timestamp').sort_index()
    return files_df


def get_loading_bar(files_list):
    """
    Create and return a loading bar (progress bar) for tracking the processing of a list of files.

    This function initializes a progress bar using `tqdm`, which can be used to visually track
    the progress of processing a list of files. The progress bar shows the number of files processed,
    the total number of files, elapsed time, and estimated time remaining.

    Parameters
    ----------
    files_list : list
        A list of files to be processed. The length of this list determines the total number of steps
        in the progress bar.

    Returns
    -------
    lding_bard : tqdm
        An initialized `tqdm` progress bar object. This object can be used in a loop to update the progress
        of file processing.
    """
    lding_bard = tqdm(total=len(files_list), ncols=100, position=0, leave=True,
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} + \
                    [Elapsed:{elapsed} Remaining:<{remaining}]')
    return lding_bard


def get_filestamp(name_list, path_file):
    """
    Extract and return the timestamp from a file name based on a specified pattern.

    This function parses the timestamp from the file name using the provided date-time pattern. 
    It supports both a single pattern and a list of patterns. The function tries each pattern 
    in sequence (if provided as a list) until it successfully extracts a timestamp.

    Parameters
    ----------
    name_list : dict
        A dictionary containing configuration parameters including the 'timestamp_pattern' which
        specifies the date-time pattern used to extract the timestamp from the file name.

    path_file : str
        The full path of the file from which to extract the timestamp. The file name is used for parsing.

    Returns
    -------
    timestamp : datetime
        A `datetime` object representing the timestamp extracted from the file name. 
    """
    file_pattern = name_list['timestamp_pattern']
    pattern_pos = name_list['pattern_position']
    # Get the file name from the path
    file_string = str(pathlib.Path(path_file).name)
    # Fit the file string to the pattern position
    file_string = file_string[pattern_pos[0]:pattern_pos[1]]
    if isinstance(file_pattern, list):
        for pattern in file_pattern:
            try:
                timestamp = datetime.strptime(file_string, pattern)
                break
            except Exception:
                continue
    else:
        timestamp = datetime.strptime(file_string, file_pattern)
    return timestamp


def get_featstamp(path_file):
    """
    Extract the timestamp from the file name assuming a specific date-time format.

    This function parses the timestamp from the file name using a fixed format pattern. 
    The file name should include a timestamp in the format '%Y%m%d_%H%M' followed by the file extension.

    Parameters
    ----------
    path_file : str
        The full path of the file from which to extract the timestamp. The file name must include a timestamp 
        in the format '%Y%m%d_%H%M' followed by '.parquet'.

    Returns
    -------
    timestamp : datetime
        A `datetime` object representing the timestamp extracted from the file name.

    Raises
    ------
    ValueError
        If the file name does not match the expected format, a `ValueError` will be raised indicating that 
        the timestamp could not be parsed.
    """
    file_string = str(pathlib.Path(path_file).name)
    timestamp = datetime.strptime(file_string, '%Y%m%d_%H%M.parquet')
    return timestamp


def get_edges(name_list, feat_files=[], read_fnc=None):
    """
    Generate the left and right edges of a domain based on the dimensions of feature files.

    This function computes the left and right edges of the domain based on the shape of the data from the 
    provided feature files. If the `edges` parameter is `True`, it retrieves the shape of the data from the 
    first non-empty feature file to define the domain edges. The function uses the provided `read_fnc` to 
    obtain the shape of the data.

    Parameters:
    ----------
    edges : bool, optional
        If `True`, compute the edges based on the dimensions of the feature files. Default is `False`.
    feat_files : list of str, optional
        List of file paths to the feature files. If `edges` is `True`, this list should contain at least one 
        valid file path. Default is an empty list.
    read_fnc : callable, optional
        A function that takes a file path as input and returns a data object with a `shape` attribute. This 
        function is used to get the shape of the data from the feature files. Default is `None`.

    Returns:
    -------
    tuple
        A tuple containing two `GeoDataFrame` objects:
        - `left_edge`: A `GeoDataFrame` representing the left edge of the domain.
        - `right_edge`: A `GeoDataFrame` representing the right edge of the domain.
    """
    # Start with empty data shape
    data_shape = (0, 0)
    if name_list['edges']:
        # Get the data shape from the first file
        for file in feat_files:
            feat_df = pd.read_parquet(file)
            if len(feat_df) > 0:
                file_path = feat_df['file'].unique()[0]
                data_shape = read_fnc(file_path).shape
                break

    # Check if lat_min is not defined
    if name_list['lat_min'] is None or name_list['lat_max'] is None:
        # Create the left and right edges
        left_edge = gpd.GeoDataFrame({'geometry': 
                                    [LineString([(data_shape[1], 0),
                                                (data_shape[1], data_shape[0])])]})
        right_edge = gpd.GeoDataFrame({'geometry':
                                    [LineString([(0, 0),
                                                (0, data_shape[0])])]})
    else:
        # Create the left and right edges
        left_edge = gpd.GeoDataFrame({'geometry': 
                                    [LineString([(name_list['lon_min'], name_list['lat_min']),
                                                (name_list['lon_min'], name_list['lat_max'])])]})
        right_edge = gpd.GeoDataFrame({'geometry':
                                    [LineString([(name_list['lon_max'], name_list['lat_min']),
                                                (name_list['lon_max'], name_list['lat_max'])])]})
    return left_edge, right_edge


def get_previous_file(current_file, prev_file, prev_list, nm_lst):
    """
    Get the previous file within a specified tolerance of the current file.

    This function attempts to find the most suitable previous file based on the timestamp of the current file
    and a list of previous files. It checks if the difference in timestamps is within a specified delta time 
    and tolerance.

    Parameters
    ----------
    current_file : str
        Path to the current file. The timestamp should be in the format '%Y%m%d_%H%M'.
    prev_files : list of str
        List of paths to previous files. The list should be sorted by timestamp in ascending order.
    prev_list : list of str
        List of paths to potential previous files to compare against.
    nm_lst : dict
        Dictionary containing 'delta_time' and 'delta_tolerance' values in minutes.

    Returns
    -------
    None
        Path to the previous file that is within the specified time tolerance of the current file, or `None`
        if no such file is found.
    """
    # Get the current file timestamp using pathlib
    current_stamp = str(pathlib.Path(current_file).name)
    current_stamp = datetime.strptime(current_stamp, '%Y%m%d_%H%M.parquet')
    dt_time = nm_lst['delta_time']
    dt_tolerance = nm_lst['delta_tolerance']
    if len(prev_file) == 0:
        return None
    # Attempt 1: compare direct with the previous file
    prev_stamp = pathlib.Path(prev_file[0]).name
    prev_stamp = datetime.strptime(prev_stamp, '%Y%m%d_%H%M.parquet')
    dt_time_calc = current_stamp - prev_stamp
    if dt_time_calc == timedelta(minutes=dt_time):
        return prev_file[0]
    elif dt_time_calc <= timedelta(minutes=dt_time + dt_tolerance):
        return prev_file[0]
    # Attempt 2: compare with the previous files in the list
    for prev_file in prev_list:
        prev_stamp = pathlib.Path(prev_file).name
        prev_stamp = datetime.strptime(prev_stamp, '%Y%m%d_%H%M.parquet')
        dt_time_calc = current_stamp - prev_stamp
        if dt_time_calc <= timedelta(minutes=dt_time + dt_tolerance):
            return prev_file
    # Attempt 3: return None
    return None  


def create_dirs(path_dir):
    """
    Create directories if they do not exist.

    Parameters
    ----------
    path_dir : str
        The path to the directory to be created. This can include multiple levels of directories.

    Returns
    -------
    path_dir : str
        The path to the created (or existing) directory.

    Notes
    -----
    The `parents=True` argument ensures that any necessary parent directories are also created.
    The `exist_ok=True` argument prevents an error from being raised if the directory already exists.
    """
    pathlib.Path(path_dir).mkdir(parents=True, exist_ok=True)
    return path_dir


def set_schema(module,name_list):
    """
    Set the schema for the output dataframe based on the module and name_list configuration.

    Parameters
    ----------
    module : str
        The name of the module for which the schema is being set. Options are 'features', 'spatial', or 'linked'.
    name_list : dict
        Dictionary containing configuration options that influence the schema, such as correction flags and validation options.

    Returns
    -------
    schema : np.dtype
        Numpy data type object describing the schema for the specified module.

    Notes:
    -----
    The schema includes different fields and their respective data types based on the module and additional corrections or validation settings.
    """
    s_dict = {
        'features': {
            'timestamp': 'datetime64[ns]',
            'cluster_id': int,
            'threshold_level': int,
            'threshold': float,
            'size': int,
            'min': float,
            'max': float,
            'mean': float,
            'std': float,
            'array_values': list,
            'array_x': list,
            'array_y': list,
            'geometry': str,
            'file': str,
            },
        'spatial': {
                'status': object,
                'threshold_level': int,
                'inside_clusters': object,
                'past_idx': list,
                'inside_idx': list,
                'merge_idx': list,
                'split_pr_idx': list,
                'split_cr_idx': list,
                'overlap': float,
                'within': bool,
                'contains': bool,
                'board': bool,
                'board_idx': list,
                'u_': float,
                'v_': float,
                'trajectory': str,
                'vector_field': str,
                'expansion': float,
            },
        'linked': {
                'cindex': int,
                'uid': int,
                'iuid': float,
                'threshold_level': int,
                'lifetime': int,
                'trajectory': str,
                'prv_mrg_uids': object,
                'prv_mrg_iuids': object,
                'prv_spl_uid': float,
                'prv_spl_iuid': float,
            }
        }
    # Add the methods field to spatial schema
    if name_list['spl_correction']:
        s_dict['spatial']['u_spl'] = float
        s_dict['spatial']['v_spl'] = float
    if name_list['mrg_correction']:
        s_dict['spatial']['u_mrg'] = float
        s_dict['spatial']['v_mrg'] = float
    if name_list['inc_correction']:
        s_dict['spatial']['u_inc'] = float
        s_dict['spatial']['v_inc'] = float
    if name_list['opt_correction']:
        s_dict['spatial']['u_opt'] = float
        s_dict['spatial']['v_opt'] = float
    if name_list['elp_correction']:
        s_dict['spatial']['u_elp'] = float
        s_dict['spatial']['v_elp'] = float
    if name_list['validation']:
        s_dict['spatial']['u_noc'] = float
        s_dict['spatial']['v_noc'] = float
        s_dict['spatial']['far'] = float
        s_dict['spatial']['method'] = str
    if name_list['validation_scores']:
        s_dict['spatial']['hit_'] = int
        s_dict['spatial']['hit_spl'] = int
        s_dict['spatial']['hit_mrg'] = int
        s_dict['spatial']['hit_inc'] = int
        s_dict['spatial']['hit_opt'] = int
        s_dict['spatial']['hit_elp'] = int
        s_dict['spatial']['false-alarm_'] = int
        s_dict['spatial']['false-alarm_spl'] = int
        s_dict['spatial']['false-alarm_mrg'] = int
        s_dict['spatial']['false-alarm_inc'] = int
        s_dict['spatial']['false-alarm_opt'] = int
        s_dict['spatial']['false-alarm_elp'] = int
        s_dict['spatial']['far_'] = float
        s_dict['spatial']['far_spl'] = float
        s_dict['spatial']['far_mrg'] = float
        s_dict['spatial']['far_inc'] = float
        s_dict['spatial']['far_opt'] = float
        s_dict['spatial']['far_elp'] = float
    # Set the schema
    schema = np.dtype(list(map(tuple, s_dict[module].items())))
    return schema               


def set_outputdf(schema):
    """
    Create an empty DataFrame with the specified schema.

    Parameters
    ----------
    schema : np.dtype
        Numpy data type object describing the schema for the DataFrame.

    Returns
    -------
    output_df : pd.DataFrame
        An empty DataFrame with columns and data types defined by the schema.
    """
    output_df = pd.DataFrame(np.empty(0, dtype=schema))
    return output_df


def set_operator(operator):
    """
    Set the comparison operator to be used.

    Parameters
    ----------
    operator : str
        A string representing the comparison operator. Valid options are:
        '>=', '<=', '>', '<', '==', '!='.

    Returns
    -------
    operator : function
        The NumPy comparison function corresponding to the input operator.

    Raises
    ------
    SystemExit
        If the operator is invalid.
    """
    if operator == '>=':
        operator = np.greater_equal
    elif operator == '<=':
        operator = np.less_equal
    elif operator == '>':
        operator = np.greater
    elif operator == '<':
        operator = np.less
    elif operator == '==':
        operator = np.equal
    elif operator == '!=':
        operator = np.not_equal
    else:
        print('Invalid operator', operator)
        print('Valid operators are: >=, <=, >, <, ==, !=')
        sys.exit()
    return operator


def set_nworkers(name_list):
    """
    Determine and set the number of worker processes.

    Parameters
    ----------
    name_list : dict
        Dictionary that may contain the key 'n_jobs' to specify the number of worker processes.

    Returns
    -------
    name_list['n_jobs'] : int
        The number of worker processes to use. If 'n_jobs' is not specified or set to -1, it defaults to the number of available CPU cores.
    """
    if 'n_jobs' not in name_list.keys():
        name_list['n_jobs'] = mp.cpu_count()
    elif name_list['n_jobs'] == -1:
        name_list['n_jobs'] = mp.cpu_count()
    return name_list['n_jobs']

def set_amemory(name_list):
    """
    Determine and set the amount of available memory for use.

    Parameters
    ----------
    name_list : dict
        Dictionary that may contain the key 'a_memory' to specify the amount of memory to use.

    Returns
    -------
    name_list['a_memory'] : int
        The amount of memory (in MB) to use, constrained by the system's available memory.
    """
    a_memory = psutil.virtual_memory().available // 1024 // 1024
    if 'a_memory' not in name_list.keys():
        name_list['a_memory'] = a_memory
    if name_list['a_memory'] > a_memory:
        name_list['a_memory'] = a_memory
    return name_list['a_memory']


def write_parquet(dataframe, path_file):
    """
    Write the DataFrame to a Parquet file with gzip compression.

    Parameters
    ----------
    dataframe : pd.DataFrame
        The DataFrame to be written to a Parquet file.

    path_file : str
        The file path where the Parquet file will be saved.

    Returns
    -------
    None
    """
    # print(path_file)
    dataframe.to_parquet(path_file,
                        engine='pyarrow',
                        compression='gzip')


def read_parquet(path_file, columns):
    """
    Read a Parquet file into a DataFrame, with optional column selection.

    Parameters
    ----------
    path_file : str
        The file path of the Parquet file to be read.

    columns : list of str, optional
        A list of column names to read from the Parquet file. If None, all columns are read.

    Returns
    -------
    dataframe : pd.DataFrame
        The DataFrame containing the data from the Parquet file.
    """
    if columns is None:
        dataframe = pd.read_parquet(path_file)
    else:
        dataframe = pd.read_parquet(path_file)
    return dataframe


def get_geotransform(name_list):
    """
    Calculate geotransform parameters based on input bounding coordinates and dimensions.

    Parameters
    ----------
    name_list : dict
        Dictionary containing the bounding coordinates and dimensions needed to calculate the geotransform.
        Expected keys: 'lon_min', 'lon_max', 'lat_min', 'lat_max', 'x_dim', 'y_dim'.

    Returns
    -------
    tuple
        A tuple containing the geotransform and its inverse.
        geotransform: (xres, 0, 0, yres, LON_MIN, LAT_MIN)
        geotransform_inv: (xres_inv, 0, 0, yres_inv, LON_MIN_inv, LAT_MIN_inv)

    Raises
    ------
    KeyError
        If any of the required keys are missing in name_list.
    """
    # Check if all keys are present in name_list and if all values is None
    if name_list['lon_min'] is None and name_list['lon_max'] \
        is None and name_list['lat_min'] is None and name_list['lat_max'] is None:
        return (1, 0, 0, 1, 0, 0), (1, 0, 0, 1, 0, 0)
    # Get the parameters
    LON_MIN = name_list['lon_min']
    LON_MAX = name_list['lon_max']
    LAT_MIN = name_list['lat_min']
    LAT_MAX = name_list['lat_max']
    X_DIM = name_list['x_dim']
    Y_DIM = name_list['y_dim']
    # Calculate pixel size
    xres = abs(LON_MAX - LON_MIN) / X_DIM
    yres = abs(LAT_MAX - LAT_MIN) / Y_DIM
    # Transform matrix
    matrix = np.array([[xres, 0, LON_MIN], [0, yres, LAT_MIN], [0, 0, 1]])
    # Calculate geotransform
    geotransform = (matrix[0, 0], matrix[0, 1], matrix[1, 0],
                    matrix[1, 1], matrix[0, 2], matrix[1, 2])
    # Calculate inverse matrix
    matrix_inv = np.linalg.inv(matrix)
    # Calculate inverse geotransform
    geotransform_inv = (matrix_inv[0, 0], matrix_inv[0, 1],
                        matrix_inv[1, 0], matrix_inv[1, 1],
                        matrix_inv[0, 2], matrix_inv[1, 2])
    return geotransform, geotransform_inv


def check_operational_system(name_list, parallel):
    # Check if the operational system is Windows
    if os.name == 'nt' and 'output_path' in name_list and 'input_path' in name_list:
        name_list['output_path'] = name_list['output_path'].replace('/', '\\')
    # Check if code is executed in IPython and operational system is not Linux
    if 'IPython' in sys.modules and platform.system() != 'Linux':
        parallel = False
    return name_list, parallel


def save_netcdf(data, name_list, output_file):
    """
    Save data to a NetCDF file.

    Parameters
    ----------
    data : np.ndarray
        The data to be saved in the NetCDF file.
        It should be a 2D array with dimensions (lat, lon).
    name_list : dict
        Dictionary containing configuration parameters including 'lat_min', 'lat_max', 'lon_min', 'lon_max',
        'x_dim', and 'y_dim' which define the spatial extent and resolution of the data.
    output_path : str
        The path where the NetCDF file will be saved. The file name will be constructed using the current date and time.
    """

    # Create longitude and latitude array
    LON_MIN = name_list['lon_min']
    LON_MAX = name_list['lon_max']
    LAT_MIN = name_list['lat_min']
    LAT_MAX = name_list['lat_max']
    lon = np.linspace(LON_MIN, LON_MAX, data.shape[-1])
    lat = np.linspace(LAT_MIN, LAT_MAX, data.shape[-2])

    # If data contains only two dimensions, expand it to three dimensions
    if data.ndim == 2:
        data = data[np.newaxis, :, :]

    # Create a DataArray with the data with dimensions (depth, lat, lon)
    da = xr.DataArray(data, dims=['threshold_level', 'lat', 'lon'], 
                      coords={'lat': lat, 'lon': lon})
    # Create a Dataset
    ds = xr.Dataset({'data': da})
    # Set attributes for the dataset
    ds.attrs['description'] = 'This is a NetCDF file containing data for the specified lat/lon grid from pyfortracc.'
    ds.attrs['created_by'] = 'pyfortracc'
    ds.attrs['created_on'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ds.attrs['lon_min'] = LON_MIN
    ds.attrs['lon_max'] = LON_MAX
    ds.attrs['lat_min'] = LAT_MIN
    ds.attrs['lat_max'] = LAT_MAX
    ds.attrs['x_dim'] = data.shape[-1]
    ds.attrs['y_dim'] = data.shape[-2]
    # Save the dataset to a NetCDF file
    # Replace file if it already exists
    if os.path.exists(output_file):
        os.remove(output_file)
    ds.to_netcdf(output_file, mode='w', format='NETCDF4',
                 encoding={'data': {'zlib': True, 'complevel': 5}})


# def calculate_pixel_area(name_list):
#     """
#     create the matrix of coordinates and vector of lat and lon.

#     Parameters
#     ----------
#     name_list : dict
#         Dictionary containing the bounding coordinates and dimensions needed to calculate the geotransform.
#         Expected keys: 'lon_min', 'lon_max', 'lat_min', 'lat_max', 'x_dim', 'y_dim'.

#     Returns
#     -------
#          matrix of the area of the pixel and the vector of lat and lon.

#     Raises
#     ------
#     KeyError
#         If any of the required keys are missing in name_list.
#     """
#     required_keys = {'lon_min', 'lon_max', 'lat_min', 'lat_max', 'x_dim', 'y_dim'}
#     if not required_keys.issubset(name_list):
#        raise KeyError(f"Missing parameters in name_list. Required keys: {required_keys}")

#     # Get the parameters
#     LON_MIN = name_list['lon_min']
#     LON_MAX = name_list['lon_max']
#     LAT_MIN = name_list['lat_min']
#     LAT_MAX = name_list['lat_max']
#     X_DIM = name_list['x_dim']
#     Y_DIM = name_list['y_dim']
#     # Calculate pixel size
#     xres = abs(LON_MAX - LON_MIN) / X_DIM
#     yres = abs(LAT_MAX - LAT_MIN) / Y_DIM
    
#     #create a matrix of longitude:
#     XLON = np.zeros((Y_DIM, X_DIM))
#     for i in range(X_DIM):
#         for j in range(Y_DIM):
#             XLON[j, i] = LON_MIN + i * xres

#     #create a matrix of latitude:
#     XLAT = np.zeros((Y_DIM, X_DIM))
#     for i in range(X_DIM):
#         for j in range(Y_DIM):
#             XLAT[j, i] = LAT_MIN + j * yres
    
#     #create the area matrix:
#     PERI = 111.32
#     PP = np.pi / 180.0
#     SURF = np.zeros((Y_DIM, X_DIM))
    
#     for j in range(1, Y_DIM-1):
#         for i in range(1, X_DIM-1):
#             # Convertendo as coordenadas para graus
#             ALAT1 = XLAT[j, i] 
#             ALAT3 = XLAT[j + 1, i] 
#             ALAT4 = XLAT[j - 1, i] 

#             ALON1 = XLON[j, i] 
#             ALON2 = XLON[j, i + 1] 
#             ALON5 = XLON[j, i - 1] 

#             # Cálculo de DY
#             DY1 = abs(ALAT1 - ALAT3) * PERI
#             DY2 = abs(ALAT1 - ALAT4) * PERI
#             DY = 0.5 * (DY1 + DY2)

#             # Cálculo de DX
#             DX1 = abs((abs(ALON1 - ALON2) * PERI) * np.cos(PP * 0.5 * (ALAT1 + ALAT3)))
#             DX2 = abs((abs(ALON1 - ALON5) * PERI) * np.cos(PP * 0.5 * (ALAT4 + ALAT1)))
#             DX = 0.5 * (DX1 + DX2)

#             # Superfície (área da célula)
#             SURF[j, i] = DX * DY

#     # Handle boundary conditions by copying adjacent values
#     SURF[0, 1:-1] = SURF[1, 1:-1]
#     SURF[-1, 1:-1] = SURF[-2, 1:-1]
#     SURF[1:-1, 0] = SURF[1:-1, 1]
#     SURF[1:-1, -1] = SURF[1:-1, -2]

#     # Handle corners
#     SURF[0, 0] = SURF[1, 1]
#     SURF[0, -1] = SURF[1, -2]
#     SURF[-1, 0] = SURF[-2, 1]
#     SURF[-1, -1] = SURF[-2, -2]
            
#     XLON = np.linspace(LON_MIN, LON_MAX, X_DIM)
#     XLAT = np.linspace(LAT_MIN, LAT_MAX, X_DIM)
    
#     return SURF, XLON, XLAT


# def haversine(lat1, lon1, lat2, lon2):
#     """
#     Calculate the great-circle distance between two points on the Earth's surface using the Haversine formula.
    
#     Parameters
#     ----------
#     lat1, lon1 : float
#         Latitude and longitude of the first point in degrees.
#     lat2, lon2 : float
#         Latitude and longitude of the second point in degrees.

#     Returns
#     -------
#     float
#         Distance between the two points in kilometers.
#     """
#     r = 6371.0  # Radius of Earth in kilometers
#     lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])  # Convert degrees to radians
    
#     dlat = lat2 - lat1
#     dlon = lon2 - lon1

#     a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
#     c = 2 * np.arcsin(np.sqrt(a))

#     return r * c  # Distance in kilometers

# def calculate_pixel_area(name_list):
#     """
#     Create the matrix of pixel areas and vectors of latitude and longitude using the Haversine formula.

#     Parameters
#     ----------
#     name_list : dict
#         Dictionary containing the bounding coordinates and dimensions needed to calculate the geotransform.
#         Expected keys: 'lon_min', 'lon_max', 'lat_min', 'lat_max', 'x_dim', 'y_dim'.

#     Returns
#     -------
#     tuple
#         surf : np.ndarray
#             Matrix of pixel areas.
#         xlon : np.ndarray
#             Vector of longitudes.
#         xlat : np.ndarray
#             Vector of latitudes.

#     Raises
#     ------
#     KeyError
#         If any of the required keys are missing in name_list.
#     """
#     required_keys = {'lon_min', 'lon_max', 'lat_min', 'lat_max', 'x_dim', 'y_dim'}
#     if not required_keys.issubset(name_list):
#         raise KeyError(f"Missing parameters in name_list. Required keys: {required_keys}")

#     # Get the parameters
#     lon_min = name_list['lon_min']
#     lon_max = name_list['lon_max']
#     lat_min = name_list['lat_min']
#     lat_max = name_list['lat_max']
#     x_dim = name_list['x_dim']
#     y_dim = name_list['y_dim']

#     # Create matrices of longitude and latitude
#     xlon = np.linspace(lon_min, lon_max, x_dim)
#     xlat = np.linspace(lat_min, lat_max, y_dim)
#     xlon, xlat = np.meshgrid(xlon, xlat)

#     # Create the area matrix
#     surf = np.zeros((y_dim, x_dim))
    
#     for j in range(1, y_dim-1):
#         for i in range(1, x_dim-1):
#             # Calculate distances using the Haversine formula
#             dy1 = haversine(xlat[j, i], xlon[j, i], xlat[j + 1, i], xlon[j, i])
#             dy2 = haversine(xlat[j, i], xlon[j, i], xlat[j - 1, i], xlon[j, i])
#             dy = 0.5 * (dy1 + dy2)

#             dx1 = haversine(xlat[j, i], xlon[j, i], xlat[j, i], xlon[j + 1, i])
#             dx2 = haversine(xlat[j, i], xlon[j, i], xlat[j, i], xlon[j - 1, i])
#             dx = 0.5 * (dx1 + dx2)

#             # Surface area (pixel area)
#             surf[j, i] = dx * dy

#     # Handle boundary conditions by copying adjacent values
#     surf[0, 1:-1] = surf[1, 1:-1]
#     surf[-1, 1:-1] = surf[-2, 1:-1]
#     surf[1:-1, 0] = surf[1:-1, 1]
#     surf[1:-1, -1] = surf[1:-1, -2]

#     # Handle corners
#     surf[0, 0] = surf[1, 1]
#     surf[0, -1] = surf[1, -2]
#     surf[-1, 0] = surf[-2, 1]
#     surf[-1, -1] = surf[-2, -2]

#     #convert xlat and xlon for a vector again:
#     xlon = np.linspace(lon_min, lon_max, x_dim)
#     xlat = np.linspace(lat_min, lat_max, y_dim)


#     return surf, xlon, xlat


# def get_pixarea(lon_in, lat_in, XLON, XLAT,SURF,default_undef = -999.99):
#     """
#     Get the pixel area for a specific lat and lon.

#     Parameters
#     ----------
#     xlon : float
#         The latitute of the pixel.
#     xlat : float
#         The longitude of the pixel.
#     SURF : matrix
#         The matrix with the pixel area.
#     XLON : array
#         The array with the longitude coordinates.
#     XLAT : array
#         The array with the latitude coordinates.

#     Returns
#     -------
#          The pixel area for the specific pixel.
#     """
#     #get the closet index for the lat and lon
#     # Find the closest index
#     index_lat = np.abs(XLAT - lat_in).argmin()
#     index_lon = np.abs(XLON - lon_in).argmin()
#     try:
#         SURF2 = SURF[index_lon, index_lat]
#     except Exception as e:
#         print(index_lon, index_lat, SURF.shape)
#         print(e)
#         return
#     # Check if the index is within the valid range
#     if index_lat < 0 or index_lat >= len(XLAT):
#         SURF2=default_undef 
#         raise ValueError(f"Index out of bounds latitude: {index_lat}. Valid range is between 0 and {len(XLAT) - 1}.")
#     if index_lon < 0 or index_lon >= len(XLON):
#         SURF2=default_undef 
#         raise ValueError(f"Index out of bounds longitude: {index_lon}. Valid range is between 0 and {len(XLON) - 1}.")

#     return SURF2