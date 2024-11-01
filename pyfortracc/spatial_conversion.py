from .spatial_conversions import boundaries, vectorfield, trajectories, clusters

def spatial_conversion(namelist,
                boundary=False, 
                vector_field=False,
                trajectorie=False,
                cluster=False,
                comp_lvl=9,
                geo_format='GPKG',
                mode='track',
                vel_unit='km/h',
                start_time='1900-01-01 00:00:00',
                end_time='2150-01-01 00:00:00'):
    '''
    This function performs spatial conversions on tracking data based on specified options. It processes boundaries, vector fields, trajectories, and clusters over a defined time range and saves them in the desired format.

    Parameters
    -------
    - `namelist` : dict 
        A dictionary containing configuration settings and file paths for spatial data.
    - `boundary` : bool, optional
        If True, processes and saves the boundaries of tracked objects. Default is False.
    - `vector_field` : bool, optional
        If True, processes and saves vector field data. Default is False.
    - `trajectorie` : bool, optional
        If True, processes and saves trajectory data. Default is False.
    - `cluster` : bool, optional
        If True, processes and saves cluster data. Default is False.
    - `comp_lvl` : int, optional
        Compression level for saving cluster data. Default is 9.
    - `geo_format` : str, optional
        Format in which to save geospatial data (e.g., 'GPKG', 'Shapefile'). Default is 'GPKG'.
    - `mode` : str, optional
        Processing mode for the spatial data (e.g., 'track'). Default is 'track'.
    - `vel_unit` : str, optional
        Unit of velocity to be used (e.g., 'km/h'). Default is 'km/h'.
    - `start_time` : str, optional
        Start time for the data processing range. Default is '1900-01-01 00:00:00'.
    - `end_time` : str, optional
        End time for the data processing range. Default is '2150-01-01 00:00:00'.
    
    This function allows flexible control over which spatial data types to process and save, based on the input flags. The results can be saved in various geospatial formats, and it operates within the specified time range.
    '''
    if boundary:
        boundaries(namelist, start_time, end_time, mode,
                vel_unit=vel_unit, driver=geo_format)
    if vector_field:
        vectorfield(namelist, start_time, end_time, mode, driver=geo_format)
    if trajectorie:
        trajectories(namelist, start_time, end_time, mode, driver=geo_format)
    if cluster:
        clusters(namelist, start_time, end_time, mode, comp_lvl)
    return