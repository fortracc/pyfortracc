import numpy as np

def new_frame(cur_frme, max_uid):
    """
    Add new clusters uids to the frame. 
    The conditions to new uids are:
    - uid is null
    - status is NEW

    Parameters
    ----------
    cur_frme : pandas.DataFrame
    Current frame.
    max_uid : int
    Maximum uid in the current frame.

    Returns
    -------
    cur_frme : pandas.DataFrame
    Current frame with new uids.
    """
    # Classify base threshold as new clusters
    new_index = cur_frme[(cur_frme['uid'].isnull()) &
                        (cur_frme['threshold_level'] == 0) &
                        (cur_frme['status'].str.contains('NEW'))].index
    if len(new_index) == 0:
        return cur_frme
    # Create the new uids for threshold 0
    uid_list = np.arange(max_uid, max_uid + len(new_index), 1, dtype=int)
    cur_frme.loc[new_index, 'uid'] = uid_list
    return cur_frme