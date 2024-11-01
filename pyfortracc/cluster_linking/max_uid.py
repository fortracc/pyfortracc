def update_max_uid(current_max_uid, global_uid):
    """
    Update the global unique identifier (UID) based on the current maximum UID.

    This function compares the 'current_max_uid' with 'global_uid' and updates 'global_uid' accordingly.
    If 'current_max_uid' is greater than or equal to 'global_uid', it increments 'global_uid' by 1.
    Otherwise, it leaves 'global_uid' unchanged.

    Parameters
    ----------
    current_max_uid : int
        The current maximum UID observed.
    global_uid : int
        The global UID that is used and needs to be updated if necessary.

    Returns
    -------
    int
        The updated global UID.
    """
    if current_max_uid >= global_uid:
        global_uid = current_max_uid + 1
    else:
        global_uid = global_uid
    return global_uid