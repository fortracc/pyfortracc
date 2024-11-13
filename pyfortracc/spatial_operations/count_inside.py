import pandas as pd

def count_inside(cur_frme, thd_lvl):
    """
    Counts the number of clusters inside of cur_df.
    
    Parameters
    ----------
    cur_frme : DataFrame
        current frame
    - threshold :  float
        threshold of current frame
    
    Returns
    ----------
    cur_thd_idx : list
        index of current threshold
    ins_thd_idx : list
        index of inside clusters
    contains : DataFrame
        index of inside clusters
    """
    # Get index of inside clusters
    ins_thd_idx = cur_frme[cur_frme['threshold_level'] > thd_lvl].index.tolist()
    if len(ins_thd_idx) == 0:
        return [], [], pd.DataFrame(columns=['index', 'index_inside',
                                            'inside_len'])
    # Get index of current threshold
    cur_thd_idx = cur_frme[cur_frme['threshold_level'] == thd_lvl].index.tolist()
    # Create cur_frme threshold frame
    cur_frme_th = cur_frme.loc[cur_thd_idx]
    # Create inside frame based on index and apply a buffer to decrease the size
    # of the geometry and apply a spatial join
    inside_frme = cur_frme.loc[ins_thd_idx]
    inside_frme.loc[:, 'geometry'] = inside_frme['geometry'].buffer(-0.001)
    # Spatial join (contains)
    contains = cur_frme_th[['geometry']].sjoin(inside_frme[['geometry']],
                                            predicate="contains",
                                            lsuffix="base", 
                                            rsuffix="inside").reset_index()
    # Pivot table and groupby to get a list of inside clusters
    contains = contains.pivot_table(columns=["index","index_inside"],
                                    aggfunc="size").reset_index()
    contains = contains.groupby('index')['index_inside'].apply(list).to_frame()
    contains['inside_len'] = contains['index_inside'].apply(lambda x: len(x))
    return cur_thd_idx, ins_thd_idx, contains
