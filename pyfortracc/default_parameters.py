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
    min_samples: int
        Number of points within eps (the point itself included) for a core
        point of the dbscan method. Default 3.
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
    new_correction: bool
        Vector correction method for NEW events. Estimates a vector for clusters
        with no previous match by averaging the vectors of the nearest neighbours.
    new_neighbors: int
        Number of nearest neighbours used by the NEW correction method.
    resume: bool
        If True, resume an interrupted run: each stage skips the files already
        completely written in output_path and cluster linking restarts from
        the last linked frame. The name_list must be the same as in the
        interrupted run. Used when calling the stages individually; in
        track() use its resume argument, which overrides this value.
    persist_uid: bool
        If True, the tracking state (next uid, cindex, iuid counters, last
        linked frame and last features frames) is saved in
        output_path/track/state/ at the end of the cluster linking. The next
        runs only process the files after the last tracked frame and continue
        its uids, iuids, lifetimes and events, which allows tracking in real
        time as new files arrive. track() does not clean the output_path
        while a state exists. Remove output_path/track/state/ to start a new
        tracking.
    save_arrays: bool
        If False, the cluster pixels (array_x, array_y and array_values columns)
        are not saved, reducing memory and disk usage. They are required by
        opt_correction and validation, so these cannot be used with
        save_arrays False. The forecast also requires them in the tracking
        table, and plot requires them when no read_function is given.
    morph_trend: bool
        Persistence forecast only. If True, each system follows its own trend
        over the observation_window: it is dilated (growing) or eroded
        (decaying) by its area trend, with a smooth border and its inner
        thresholds kept nested, and its values follow the trend of its mean,
        kept inside their threshold levels. The trends fade with the lead time.
        Not applied with the '==' and '!=' operators. Default False. Its
        settings are fixed in pyfortracc/forecast/morphology.py.
    forecast_mode: str
        'persistence' (default), 'lstm' or 'gru'. The recurrent modes (with
        PyTorch) read the history of each system in
        the tracking table and predict, for the next time step, a correction
        of its persistence displacement, its area rate and the change of its
        values. The forecast image is drawn like the persistence one (moved,
        dilated/eroded systems) and enters the tracking cycle again at every
        lead time. The model runs on the best device available (CUDA, TPU,
        Apple MPS or CPU). See pyfortracc/forecast/rnn_model.py.
        'flow' (with PyTorch): residual flow matching. The network draws the
        next image as a correction of the persistence + morph_trend image
        (growth, decay, deformation and new systems), reading the last frames,
        maps of the history of the systems and the optical flow of the
        tracking. Not available with the '==' and '!=' operators. See
        pyfortracc/forecast/flow_model.py.
    rnn_weights: str or None
        Learned modes ('lstm', 'gru', 'flow') only. None (default): the model
        is trained (see rnn_train_period) and saved in
        output_path/forecast/models/, where the next calls with the same
        settings reuse it. Its file name tells the mode, the training period,
        the operator and thresholds, delta_time, observation_window and the
        architecture, e.g.
        lstm_202511050000-202511051200_le235-220-210_dt10min_win3_h32l1seq6_<hash>.pt
        (seq6: the network reads the last 6 time steps of each system). A
        path: the weights of a trained model (a .pt file written by a
        previous run), used for inference only.
    rnn_train_period: None or [start, end]
        Learned modes only. None (default): the model is trained on the
        whole tracking up to forecast_time (it never learns from frames after
        the forecast start). [start, end] (timestamps, e.g.
        ['2025-11-05 00:00', '2025-11-05 12:00']): trained on the frames of
        that period only.
    rnn_aux: list of str
        Learned modes only. Extra columns of the tracking table used as
        inputs of the model (e.g. ['land_use'] or the columns added by
        post_processing.add_raster_data, such as 'dbz' or 'dbz_mean'). Numeric
        columns are used as they are and columns of arrays by their mean.
        Default [].
    rnn_arch: None, dict or 'optuna'
        Learned modes only. None (default): the default architecture.
        A dict overrides some of its settings. 'lstm' and 'gru': hidden (32),
        layers (1), dropout (0.1), seq_len (6, time steps of history read by
        the model), lr (3e-3), weight_decay (1e-4) and device ('auto', or e.g.
        'cpu', 'cuda', 'mps'); 'optuna': the settings are searched with optuna
        within a small time budget. 'flow': base (32, channels of the first
        level of the network), lr (2e-4), weight_decay (1e-4) and device.
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
    if 'morph_trend' not in name_lst:
        name_lst['morph_trend'] = False
    if 'rnn_weights' not in name_lst:
        name_lst['rnn_weights'] = None
    if 'rnn_aux' not in name_lst:
        name_lst['rnn_aux'] = []
    if 'rnn_arch' not in name_lst:
        name_lst['rnn_arch'] = None
    if 'rnn_train_period' not in name_lst:
        name_lst['rnn_train_period'] = None
    if 'mean_dbz' not in name_lst:
        name_lst['mean_dbz'] = False
    if 'cluster_method' not in name_lst:
        name_lst['cluster_method'] = 'ndimage'
    if 'eps' not in name_lst:
        name_lst['eps'] = 1
    if 'min_samples' not in name_lst:
        name_lst['min_samples'] = 3
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
    if 'new_correction' not in name_lst:
        name_lst['new_correction'] = False
    if 'new_neighbors' not in name_lst:
        name_lst['new_neighbors'] = 3
    if 'resume' not in name_lst:
        name_lst['resume'] = False
    if 'default_columns' not in name_lst:
        name_lst['default_columns'] = True
    if 'validation' not in name_lst:
        name_lst['validation'] = False
    if 'validation_scores' not in name_lst:
        name_lst['validation_scores'] = False
    # TODO: add calc_dir and calc_speed
    if 'calc_dir' not in name_lst:
        name_lst['calc_dir'] = False
    # TODO: add speed_units
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
    if 'spl_expansion' not in name_lst:
        name_lst['spl_expansion'] = False
    if 'persist_uid' not in name_lst:
        name_lst['persist_uid'] = False
    if 'save_arrays' not in name_lst:
        name_lst['save_arrays'] = True
    # The cluster pixels are read from the features files by these methods
    if not name_lst['save_arrays']:
        needs_arrays = [key for key in ('opt_correction', 'validation')
                        if name_lst[key]]
        if needs_arrays:
            needs_arrays = ' and '.join(needs_arrays)
            raise ValueError("name_list['save_arrays'] = False cannot be used "
                             "with {0}, which require the array_x, array_y and "
                             "array_values columns. Set save_arrays to True "
                             "or disable {0}.".format(needs_arrays))
    # Settings of the learned forecast modes
    if name_lst['forecast_mode'] not in ('persistence', 'lstm', 'gru', 'flow'):
        raise ValueError("name_list['forecast_mode'] must be 'persistence', "
                         "'lstm', 'gru' or 'flow', not {!r}.".format(name_lst['forecast_mode']))
    if name_lst['forecast_mode'] == 'flow' and name_lst['operator'] in ('==', '!='):
        raise ValueError("forecast_mode 'flow' needs an ordered operator ('>', '>=', '<', '<=').")
    if isinstance(name_lst['rnn_aux'], str):
        name_lst['rnn_aux'] = [name_lst['rnn_aux']]
    arch = name_lst['rnn_arch']
    if name_lst['forecast_mode'] == 'flow':
        arch_keys = {'base', 'lr', 'weight_decay', 'device'}
        if not (arch is None or isinstance(arch, dict)):
            raise ValueError("name_list['rnn_arch'] must be None or a dict with forecast_mode 'flow'.")
    else:
        arch_keys = {'hidden', 'layers', 'dropout', 'seq_len', 'lr', 'weight_decay', 'device'}
    if not (arch is None or arch == 'optuna' or isinstance(arch, dict)):
        raise ValueError("name_list['rnn_arch'] must be None, a dict or 'optuna'.")
    period = name_lst['rnn_train_period']
    if period is not None and (not isinstance(period, (list, tuple)) or len(period) != 2):
        raise ValueError("name_list['rnn_train_period'] must be None or [start, end].")
    if isinstance(arch, dict) and set(arch) - arch_keys:
        raise ValueError("Unknown keys in name_list['rnn_arch']: {}. Valid keys: {}.".format(
            sorted(set(arch) - arch_keys), sorted(arch_keys)))
    return name_lst
