import glob
import os
import sys
import psutil


def get_input_files(input_path):
    ''' 
    This function retrieves and returns a sorted list of all files within a specified directory and its subdirectories.

    Parameters
    -------
    - `input_path` : str 
        The root directory path from which to search for files.

    Returns
    -------
    - `files_list` : list
        A sorted list of file paths found within `input_path` and its subdirectories.
    '''
    files_list = sorted(glob.glob(input_path + '**/*', recursive=True))
    files_list = [file for file in files_list if os.path.isfile(file)]
    if not files_list:
        print('Input path is empty', input_path)
        sys.exit()
    return files_list


def default_parameters(name_lst=None, read_function=None):
    '''Default parameters for the pyfortracc module

    Parameters
    -------
    name_lst : dict
        Dictionary with the parameters to be used.
    read_function : function
        Function to read the data.
    mean_dbz: bool
        If True, the mean reflectivity is used to perform the tracking.
    cluster_method: str
        Method to perform the clustering. It can be 'dbscan' or 'ndimage'.
    eps: int
        Epsilon distance to be used in the clustering for the dbscan method.
    delta_tolerance: int
        Delta tolerance is the maximum time difference between two files.
    num_prev_skip: int
        Number of previous files to skip.
    edges: str
        Is the edge of the domain to be used. It can be 'left' or 'right'.
        It is used to perform the cluster linking in the edges of the domain.
    n_jobs: int
        Number of jobs to run in parallel.
    min_overlap: int
        Minimum overlap between two clusters to be considered as the same.
    x_dim: int and y_dim: int
        Dimensions of the data.
    lat_min: float
        Minimum latitude.
    lon_min: float
        Minimum longitude.
    lat_max: float
        Maximum latitude.
    lon_max: float
        Maximum longitude.
    y_res: float
        Resolution in the y axis in degrees.
    x_res: float
        Resolution in the x axis in degrees.
    convex_hull: bool
        If True, the convex hull is used to calculate the geometry of the clusters.
    preserv_split: bool
        If True, the split lifetime events are preserved for NEW/SPLIT events.
    spl_correction: bool
        Vector correction method for split events.
    mrg_correction: bool
        Vector correction method for merge events.
    inc_correction: bool
        Vector correction method for inner cells.
    opt_correction: bool
        Vector correction method for optical flow.
    opt_mtd: str
        Optical flow method. It can be 'farneback' or 'lucas-kanade'
    elp_correction: bool
        Vector correction method for ellipse fitting.
    'epsg': int
        EPSG code for the projection.
    Returns
    -------
    name_lst : dict
        Dictionary with the parameters to be used.
    '''
    # Set default parameters
    if 'track_start' not in name_lst:
        name_lst['track_start'] = None
    if 'track_end' not in name_lst:
        name_lst['track_end'] = None
    if 'forecast_time' not in name_lst:
        name_lst['forecast_time'] = None
    if 'forecast_mode' not in name_lst:
        name_lst['forecast_mode'] = 'persistence'
    if 'observation_window' not in name_lst:
        name_lst['observation_window'] = None
    if 'lead_time' not in name_lst:
        name_lst['lead_time'] = None
    if 'mean_dbz' not in name_lst:
        name_lst['mean_dbz'] = False
    if 'cluster_method' not in name_lst:
        name_lst['cluster_method'] = 'ndimage'
    if 'eps' not in name_lst:
        name_lst['eps'] = 1
    if 'delta_tolerance' not in name_lst:
        name_lst['delta_tolerance'] = 0
    if 'pattern_position' not in name_lst:
        name_lst['pattern_position'] = [None,None]
    if 'num_prev_skip' not in name_lst:
        name_lst['num_prev_skip'] = 0
    if 'edges' not in name_lst:
        name_lst['edges'] = False
    if 'n_jobs' not in name_lst:
        name_lst['n_jobs'] = -1
    if 'a_memory' not in name_lst:
        a_memory = psutil.virtual_memory().available / 1024 / 1024 / 1024
        name_lst['a_memory'] = a_memory
    if 'temp_folder' not in name_lst:
        name_lst['temp_folder'] = '/tmp'
    if 'min_overlap' not in name_lst:
        name_lst['min_overlap'] = 10
    if 'x_dim' not in name_lst or 'y_dim' not in name_lst:
        files = get_input_files(name_lst['input_path'])
        for file in files:
            if read_function:
                data = read_function(file)
                name_lst['y_dim'], name_lst['x_dim'] = data.shape
                break
    if 'lat_min' not in name_lst:
        name_lst['lat_min'] = None
    if 'lon_min' not in name_lst:
        name_lst['lon_min'] = None
    if 'lat_max' not in name_lst:
        name_lst['lat_max'] = None
    if 'lon_max' not in name_lst:
        name_lst['lon_max'] = None
    if name_lst['lat_min'] == None and name_lst['lat_max'] == None or read_function == None:
        name_lst['y_res'] = 1
        name_lst['x_res'] = 1
    else:
        name_lst['y_res'] = abs(name_lst['lat_min'] - name_lst['lat_max']) / name_lst['y_dim']
        name_lst['x_res'] = abs(name_lst['lon_min'] - name_lst['lon_max']) / name_lst['x_dim']
    if 'convex_hull' not in name_lst:
        name_lst['convex_hull'] = False
    if 'preserv_split' not in name_lst:
        name_lst['preserv_split'] = False
    if 'spl_correction' not in name_lst:
        name_lst['spl_correction'] = False
    if 'mrg_correction' not in name_lst:
        name_lst['mrg_correction'] = False
    if 'inc_correction' not in name_lst:
        name_lst['inc_correction'] = False
    if 'opt_correction' not in name_lst:
        name_lst['opt_correction'] = False
    if 'opt_mtd' not in name_lst:
        name_lst['opt_mtd'] = 'lucas-kanade'
    if 'elp_correction' not in name_lst:
        name_lst['elp_correction'] = False
    if 'default_columns' not in name_lst:
        name_lst['default_columns'] = True
    if 'validation' not in name_lst:
        name_lst['validation'] = False
    if 'validation_scores' not in name_lst:
        name_lst['validation_scores'] = False
    # TODO: add calc_dir and calc_speed
    if 'calc_dir' not in name_lst:
        name_lst['calc_dir'] = False
    if 'calc_speed' not in name_lst:
        name_lst['calc_speed'] = False
        name_lst['speed_units'] = 'm/s'
    # TODO: add epsg
    if 'epsg' not in name_lst:
        name_lst['epsg'] = 4326
    if 'prv_uid' not in name_lst:
        name_lst['prv_uid'] = False
    if 'mrg_expansion' not in name_lst:
        name_lst['mrg_expansion'] = False
    return name_lst
