import glob
import json
import os
import pathlib
import shutil
import pandas as pd
from .utils import get_featstamp

STATE_VERSION = 1


def state_path(name_lst):
    """
    Return the directory of the persisted tracking state.

    The state is kept in output_path/track/state/ and holds everything the
    cluster linking needs to continue in a later run: the next uid, the
    cindex, the iuid counters, the last linked frame and the last features
    frames (used by the spatial operations of the first new frame).

    Parameters
    ----------
    name_lst : dict
        Dictionary with the parameters to be used.

    Returns
    -------
    str
        Path of the state directory.
    """
    return name_lst['output_path'] + 'track/state/'


def state_exists(name_lst):
    """ Check if persist_uid is enabled and a state was already saved. """
    return (name_lst.get('persist_uid', False) and
            os.path.isfile(state_path(name_lst) + 'state.json'))


def load_state(name_lst):
    """
    Load the persisted tracking state.

    Parameters
    ----------
    name_lst : dict
        Dictionary with the parameters to be used.

    Returns
    -------
    dict or None
        The state, or None if persist_uid is disabled or no state was saved.
        Keys: last_stamp, prv_stamp, uid_iter, cindex, iuid_cnt, features
        (list of paths) and linked (path).
    """
    if not state_exists(name_lst):
        return None
    path = state_path(name_lst)
    with open(path + 'state.json') as state_file:
        state = json.load(state_file)
    thresholds = [float(thld) for thld in name_lst['thresholds']]
    if state['thresholds'] != thresholds:
        raise ValueError("The thresholds {} of the name_list differ from the "
                         "thresholds {} of the persisted state in {}. Use the "
                         "same thresholds or remove the state directory to "
                         "start a new tracking.".format(thresholds,
                                                        state['thresholds'],
                                                        path))
    state['last_stamp'] = pd.Timestamp(state['last_stamp'])
    state['prv_stamp'] = pd.Timestamp(state['prv_stamp'])
    state['iuid_cnt'] = {tuple(int(val) for val in key.split(':')): n
                         for key, n in state['iuid_cnt'].items()}
    state['features'] = [path + 'features/' + file
                         for file in state['features']]
    state['linked'] = path + 'linked/' + state['linked']
    return state


def save_state(name_lst, feat_files, linked_file, last_stamp, prv_stamp,
               uid_iter, cindex, iuid_cnt):
    """
    Save the tracking state at the end of the cluster linking.

    The parquet files are copied with their time stamp names and the
    state.json is replaced last, so an interrupted save keeps the previous
    state valid. Files no longer referenced are removed afterwards.

    Parameters
    ----------
    name_lst : dict
        Dictionary with the parameters to be used.
    feat_files : list of str
        Features files of the last frames, in time order. Only the last
        max(2, num_prev_skip + 1) are kept, as used by get_previous_file.
    linked_file : str
        Linked file of the last frame.
    last_stamp : datetime
        Time stamp of the last processed frame. Later runs only process
        frames after it.
    prv_stamp : datetime
        Time stamp of the last non empty frame, used by the linking.
    uid_iter : int
        Next free uid.
    cindex : int
        Last cindex.
    iuid_cnt : dict
        Counters {(uid, threshold_level): suffix} of the inner clusters.
    """
    path = state_path(name_lst)
    for folder in ('features/', 'linked/'):
        pathlib.Path(path + folder).mkdir(parents=True, exist_ok=True)
    n_keep = max(2, name_lst['num_prev_skip'] + 1)
    feat_files = feat_files[-n_keep:]
    for feat_file in feat_files:
        _copy(feat_file, path + 'features/')
    _copy(linked_file, path + 'linked/')
    state = {'version': STATE_VERSION,
             'thresholds': [float(thld) for thld in name_lst['thresholds']],
             'last_stamp': str(pd.Timestamp(last_stamp)),
             'prv_stamp': str(pd.Timestamp(prv_stamp)),
             'uid_iter': int(uid_iter),
             'cindex': int(cindex),
             'iuid_cnt': {'{}:{}'.format(uid, level): int(n)
                          for (uid, level), n in iuid_cnt.items()},
             'features': [pathlib.Path(file).name for file in feat_files],
             'linked': pathlib.Path(linked_file).name}
    with open(path + 'state.json.tmp', 'w') as state_file:
        json.dump(state, state_file, indent=2)
    os.replace(path + 'state.json.tmp', path + 'state.json')
    # Remove the files of previous states
    for folder, keep in (('features/', state['features']),
                         ('linked/', [state['linked']])):
        for file in glob.glob(path + folder + '*'):
            if pathlib.Path(file).name not in keep:
                os.remove(file)


def new_files(files, state, stamp_fnc=get_featstamp):
    """
    Keep only the files after the last frame of the persisted state.

    Parameters
    ----------
    files : list of str
        Files to be filtered.
    state : dict or None
        State returned by load_state. If None, files is returned unchanged.
    stamp_fnc : function
        Function that returns the time stamp of a file.

    Returns
    -------
    list of str
        The files after state['last_stamp'].
    """
    if state is None:
        return files
    return [file for file in files if stamp_fnc(file) > state['last_stamp']]


def _copy(src_file, dst_path):
    """ Copy a file into dst_path, replacing it atomically. """
    dst_file = dst_path + pathlib.Path(src_file).name
    if os.path.abspath(src_file) == os.path.abspath(dst_file):
        return
    shutil.copyfile(src_file, dst_file + '.tmp')
    os.replace(dst_file + '.tmp', dst_file)
