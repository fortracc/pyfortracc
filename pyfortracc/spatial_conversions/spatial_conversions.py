from .boundaries import boundaries
from .vectorfield import vectorfield
from .trajectories import trajectories
from .clusters import clusters

def spatial_conversions(name_list = None, read_function=None, boundary = True, vector_field = False, trajectory = True, cluster = True,
                        start_time = None, end_time = None, vel_unit = 'km/h', driver='GeoJSON'):
    """
    This function handles spatial data processing by invoking several sub-functions to perform different spatial conversions.
    
    Parameters
    -------
    - name_list: dict
        Dictionary containing various configuration parameters, including spatial boundaries and grid dimensions.
    - boundary: bool
        Whether to perform boundary processing. Default is True.
    - vector_field: bool
        Whether to process vector fields. Default is False.
    - trajectory: bool
        Whether to process trajectories. Default is True.
    - cluster: bool
        Whether to process clusters. Default is True.
    - start_time: str or pd.Timestamp
        The starting timestamp for the data to process.
    - end_time: str or pd.Timestamp
        The ending timestamp for the data to process.
    - vel_unit: str, optional
        The velocity unit for boundary processing. Default is 'km/h'.
    - driver: str, optional
        The file format driver to use for output files. Default is 'GeoJSON'.
    
    Returns
    -------
    None
    """
    if not 'lon_min' in name_list and not 'lon_max' in name_list \
        and not 'lat_min' in name_list and not 'lat_max' in name_list \
        and not 'x_dim' in name_list and not 'y_dim' in name_list:
            print('Please, set the spatial boundaries in the name_list dictionary')
            print('lon_min, lon_max, lat_min, lat_max, x_dim, y_dim')
            return
    
    if boundary:
        boundaries(name_list, start_time, end_time, vel_unit, driver)
    if vector_field:
        vectorfield(name_list, start_time, end_time, driver)
    if trajectory:
        trajectories(name_list, start_time, end_time, driver)
    if cluster:
        clusters(name_list, start_time, end_time, read_function)
