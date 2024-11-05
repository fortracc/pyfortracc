import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def validation(cur_frame, prv_frame, name_list):
    """
    Validates correction methods by comparing the current frame with the previous frame.

    Parameters
    ----------
    cur_frame : pd.DataFrame
        DataFrame representing the current frame, which includes corrected and original data.
    prv_frame : pd.DataFrame
        DataFrame representing the previous frame used for comparison.
    name_list : dict
        Dictionary containing configuration settings, including:
        - 'validation_scores': bool
            Flag indicating if validation scores should be included in the output.

    Returns
    -------
    cur_frame : pd.DataFrame
        Updated current frame DataFrame with validation results and optional validation scores.
    """
    # Get u columns except u_noc
    u_cols = cur_frame.columns[cur_frame.columns.str.contains('u_') &
                                ~cur_frame.columns.str.contains('noc')]
    v_cols = cur_frame.columns[cur_frame.columns.str.contains('v_') &
                                ~cur_frame.columns.str.contains('noc')]
    # Apply x_res and y_res to u_cols and v_cols
    cur_frame[u_cols] = cur_frame[u_cols] / name_list['x_res']
    cur_frame[v_cols] = cur_frame[v_cols] / name_list['y_res']
    # Select not nan values of prev_idx
    cur_prv_frame = cur_frame[~cur_frame['past_idx'].isna()]
    prv_y = prv_frame.loc[cur_prv_frame['past_idx']]['array_y']
    prv_x = prv_frame.loc[cur_prv_frame['past_idx']]['array_x']
    # Get the cluster points of prv_frame (Previous is t - 1) and add to cur_frame rows
    cur_prv_frame.loc[cur_prv_frame.index, 'prev_y'] = prv_y.values
    cur_prv_frame.loc[cur_prv_frame.index, 'prev_x'] = prv_x.values
    # Add columns prev_y and prev_x to list of u_v columns
    # u_v_cols = u_v_cols.insert(0, 'array_y')
    # u_v_cols = u_v_cols.insert(1, 'array_x')
    # u_v_cols = u_v_cols.insert(2, 'prev_y')
    # u_v_cols = u_v_cols.insert(3, 'prev_x')
    # print(u_v_cols)
    # Calculate the scores
    methods = cur_prv_frame.apply(lambda row: extrapolate(row, u_cols, v_cols), axis=1)
    if methods.empty:
        # Return u_cols and v_cols to original values
        cur_frame[u_cols] = cur_frame[u_cols] * name_list['x_res']
        cur_frame[v_cols] = cur_frame[v_cols] * name_list['y_res']
        return cur_frame
    cur_frame.loc[methods.index, 'u_'] = methods['u_']
    cur_frame.loc[methods.index, 'v_'] = methods['v_']
    cur_frame.loc[methods.index, 'far'] = methods['far']
    cur_frame.loc[methods.index, 'method'] = methods['method']
    # Drop the columns from the methods
    methods = methods.drop(columns=['u_', 'v_', 'far', 'method'])
    if name_list['validation_scores']:
        # Delete methods columns from cur_frame
        cur_frame = cur_frame.drop(columns=methods.columns)
        # Join the methods to cur_frame
        cur_frame = cur_frame.join(methods)
    # Return u_cols and v_cols to original values
    cur_frame[u_cols] = cur_frame[u_cols] * name_list['x_res']
    cur_frame[v_cols] = cur_frame[v_cols] * name_list['y_res']
    return cur_frame

def extrapolate(row, u_, v_):
    """
    Extrapolates the previous cluster to the current frame and evaluates the correction methods.

    Parameters
    ----------
    row : pd.Series
        A Series representing a single row from the DataFrame with both current and previous cluster data,
        including velocity fields and previous cluster coordinates.

    Returns
    -------
    row : pd.Series
        The updated row with evaluation metrics for each correction method, including:
        - 'u_': Extrapolated u velocity.
        - 'v_': Extrapolated v velocity.
        - 'far': False Alarm Rate (FAR) of the best method.
        - 'method': The name of the best correction method.
    """
    # Set current cluster points
    cur_cluster = tuple(zip(row['array_y'], row['array_x']))
    # Loop over the methods
    used_methods = []
    best_method = pd.DataFrame()
    for uv in range(len(u_)):
        # Get u and v values and round to int
        mtd_u, mtd_v = row[u_[uv]], row[v_[uv]]
        mtd_u = np.round(mtd_u).astype(int)
        mtd_v = np.round(mtd_v).astype(int)
        mtd_u = mtd_u + row['prev_y'] # Apply method to previous cluster
        mtd_v = mtd_v + row['prev_x'] # Apply method to previous cluster
        # Create a tuple with the extrapolated previous cluster
        prv_cluster = tuple(zip(mtd_u, mtd_v))
        # Compute the scores
        hit = len(set(prv_cluster).intersection(set(cur_cluster)))
        false_ = len(set(prv_cluster).difference(set(cur_cluster)))
        far = false_ / (hit + false_)
        # Add to row for each method
        row['hit' + str(u_[uv][1:])] = hit
        row['false-alarm' + str(u_[uv][1:])] = false_
        row['far' + str(u_[uv][1:])] = far
        used_methods.append('hit' + str(u_[uv][1:]))
        used_methods.append('false-alarm' + str(u_[uv][1:]))
        used_methods.append('far' + str(u_[uv][1:]))
        # Add to main far
        best_method = pd.concat([best_method, pd.DataFrame(
                                            [far, # Get the far value
                                            u_[uv][2:], # Get the method name
                                            row[u_[uv]], # Get the u_ value
                                            row[v_[uv]]], # Get the v_ value
                                            index=['far', 'method', 'u_', 'v_']).T])
    # Fill '' at column method with none
    best_method['method'] = best_method['method'].replace('', 'noc') # noc = no correction
    # Select the used methods and the best method
    row = row[used_methods]
    best_method = best_method.sort_values(by='far', ascending=True).iloc[0]
    row['u_'] = best_method['u_']
    row['v_'] = best_method['v_']
    row['far'] = best_method['far']
    row['method'] = best_method['method']
    return row