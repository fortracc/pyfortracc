import pandas as pd

def board_clusters(cur_frame):
    """
    Copy values from board_idx to board_idx. The board_idx is the index of
    the clusters that are touching the board.     
    
    Parameters
    ----------
    cur_frame : pandas dataframe
        Current dataframe.
        
    Returns
    -------
    cur_frame : pandas dataframe
        Updated dataframe.
    """  
    board_idx = cur_frame[(cur_frame['board'] == True)]
    if board_idx.empty:
        return cur_frame
    current_index = cur_frame.loc[board_idx.index]
    touching_idx = pd.Index(current_index['board_idx'].values.astype(int))
    board_uids = cur_frame.loc[touching_idx]['uid'].values
    board_iuids = cur_frame.loc[touching_idx]['iuid'].values
    board_status = cur_frame.loc[touching_idx]['status'].values
    cur_frame.loc[board_idx.index,'uid'] = board_uids
    cur_frame.loc[board_idx.index,'iuid'] = board_iuids
    cur_frame.loc[board_idx.index,'status'] = board_status
    return cur_frame