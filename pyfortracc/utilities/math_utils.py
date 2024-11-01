import numpy as np

def uv_components(p0, p1):
    """ 
    This function calculates the zonal (u) and meridional (v) components between two points.
    
    Parameters
    ----------
    p0 : tuple or list
        The coordinates (x, y) of the starting point.
    p1 : tuple or list
        The coordinates (x, y) of the ending point.
    
    Returns
    -------
    u : float
        The zonal component, representing the difference in the x-coordinates (p1[0] - p0[0]).
    v : float
        The meridional component, representing the difference in the y-coordinates (p1[1] - p0[1]).
    """
    u = p1[0] - p0[0]
    v = p1[1] - p0[1]
    return u, v


def calc_addition_uv(uv_list):
    """ 
    This function takes a list of pairs of u and v values, and calculates the sum of all uu values and 
    the sum of all vv values separately.
    
    Parameters
    ----------
    uv_list : list of tuples or list of lists
        A list where each element is a pair (u, v) representing the zonal and meridional components.
    
    Returns
    -------
    u : list
        The sum of all zonal (u) components.
    v : list
        The sum of all meridional (v) components.
    """
    uv_array = np.array(uv_list)
    u_add = np.sum(uv_array[:,0])
    v_add = np.sum(uv_array[:,1])
    return u_add, v_add


def calc_mean_uv(uv_list):
    """ 
    This function calculates the mean of the zonal (u) and meridional (v) components 
    from a list of vector pairs.
    
    Parameters
    ----------
    uv_list : list of tuples or list of lists
        A list where each element is a pair (u, v) 

    Returns
    -------
    u_mean : float
        The mean value of the zonal (u) components.
    v_mean : float
        The mean value of the meridional (v) components.
    
    Notes
    -------
    u : float
        The zonal component, representing the east-west direction (zonal).
    v : float
        The meridional component, representing the north-south direction (meridional).
    """
    uv_array = np.array(uv_list)
    u_mean = np.mean(uv_array[:,0])
    v_mean = np.mean(uv_array[:,1])
    return u_mean, v_mean


def uv2angle(u, v):
    """ 
    This function calculates the angle in degrees from the zonal (u) and meridional (v) components.

    Parameters
    ----------
    u : float
        The zonal component, representing the east-west direction.
    v : float
        The meridional component, representing the north-south direction.
    
    Returns
    -------
    angle : float
        The angle in degrees measured counterclockwise from the positive x-axis (east).
        The angle is adjusted to be in the range [0, 360) degrees.
    """
    radians_ = np.arctan2(v, u)
    angle = np.degrees(radians_)
    if angle < 0:
        angle = angle + 360
    return angle


def angle2uv(angle):
    """ 
    This function calculates the zonal (u) and meridional (v) components from an angle in degrees.

    Parameters
    ----------
    angle : float
        The angle in degrees, measured counterclockwise from the positive x-axis (east direction).
    
    Returns
    -------
    u : float
        The zonal component, representing the east-west direction.
    v : float
        The meridional component, representing the north-south direction.
    """
    radians_ = np.radians(angle)
    u = np.cos(radians_)
    v = np.sin(radians_)
    return u, v


def uv2magn(u, v):
    """ 
    This function calculates the magnitude of a vector from its zonal (u) and meridional (v) components.

    Parameters
    ----------
    u : float
        The zonal component, representing the east-west direction.
    v : float
        The meridional component, representing the north-south direction.
    
    Returns
    -------
    magnitude : float
        The magnitude of the vector, computed as the Euclidean norm of the components (sqrt(u^2 + v^2)).
    """
    magnitude = np.sqrt(u**2 + v**2)
    return magnitude


def magnitude2uv(magnitude, angle):
    """ 
    This function calculates the zonal (u) and meridional (v) components from a magnitude and an angle.

    Parameters
    ----------
    magnitude : float
        The magnitude of the vector, representing its length.
    angle : float
        The angle in degrees, measured counterclockwise from the positive x-axis (east direction).
    
    Returns
    -------
    u : float
        The zonal component, calculated as the product of the magnitude and the cosine of the angle.
    v : float
        The meridional component, calculated as the product of the magnitude and the sine of the angle.
    """
    radians_ = np.radians(angle)
    u = magnitude * np.cos(radians_)
    v = magnitude * np.sin(radians_)
    return u, v


def calculate_angle(p0, p1):
    """ 
    This function calculates the angle between two points in degrees.

    Parameters
    ----------
    p0 : tuple or list
        The coordinates (x, y) of the starting point.
    p1 : tuple or list
        The coordinates (x, y) of the ending point.
    
    Returns
    -------
    angle : float
        The angle in degrees between the line connecting the two points and the positive x-axis (east direction).
        The angle is adjusted to be in the range [0, 360) degrees.
    """
    radians_ = np.arctan2(p1[1] - p0[1],
                        p1[0] - p0[0])
    angle = np.degrees(radians_)
    if angle < 0:
        angle = angle + 360
    return angle


def calculate_magnitude(p0, p1):
    """ 
    This function calculates the magnitude (Euclidean distance) between two points.

    Parameters
    ----------
    p0 : tuple or list
        The coordinates (x, y) of the starting point.
    p1 : tuple or list
        The coordinates (x, y) of the ending point.
    
    Returns
    -------
    magnitude : float
        The Euclidean distance between the two points, calculated as the square root of the sum of the squared differences in x and y coordinates.
    """
    magnitude = np.sqrt((p1[0] - p0[0])**2 + (p1[1] - p0[1])**2)
    return magnitude

def point_position(x1 = None, y1 = None, magnitude = None, angle = None):
    """
    Calculate the position of a new point based on a starting point, magnitude, and angle.

    Parameters
    ----------
    x1 : float, optional
        The x-coordinate of the starting point. Default is None.
    y1 : float, optional
        The y-coordinate of the starting point. Default is None.
    magnitude : float, optional
        The magnitude or distance to move from the starting point. Default is None.
    angle : float, optional
        The angle in degrees, measured counterclockwise from the positive x-axis (east direction), at which to move. Default is None.

    Returns
    -------
    x2 : float
        The x-coordinate of the new point, calculated using the starting point, magnitude, and angle.
    y2 : float
        The y-coordinate of the new point, calculated using the starting point, magnitude, and angle.
    
    Notes
    -----
    - The angle is converted from degrees to radians before computation.
    - If x1, y1, magnitude, or angle are not provided (i.e., are None), the function will raise an error due to missing values.
    """
    rad_theta = np.radians(angle)
    x2 = x1 + magnitude * np.cos(rad_theta)
    y2 = y1 + magnitude * np.sin(rad_theta)
    return x2, y2

def calculate_vel(magnitude, vel_unit, pixel_size, delta):
    """ 
    Calculate the velocity from an array of magnitudes given a unit of velocity.

    Parameters
    ----------
    magnitude : array-like
        The array of magnitudes, typically in pixels or other measurement units.
    vel_unit : str
        The unit of velocity to convert to. Options are 'km/h', 'm/s', or 'mp/h'.
    pixel_size : float
        The size of each pixel in meters or kilometers, depending on the velocity unit.
    delta : float
        The time interval in minutes over which the magnitude was measured.

    Returns
    -------
    velocity : array-like
        The calculated velocity in the specified unit of measurement.

    Notes
    -----
    - The conversion factors used are:
        - For 'km/h': 1 pixel = 111.32 km (approximated)
        - For 'm/s': 1 pixel = 111320 meters (approximated)
        - For 'mp/h': 1 pixel = 69.17 miles (approximated)
    - delta should be provided in minutes. The formula assumes delta is the total time for the entire magnitude measurement.
    """
    if vel_unit == 'km/h':
        pixel_size = pixel_size * 111.32
        velocity = magnitude * pixel_size / (delta / 60)
    elif vel_unit == 'm/s':
        pixel_size = pixel_size * 111320
        velocity = magnitude * pixel_size / (delta * 60)
    elif vel_unit == 'mp/h':
        pixel_size = pixel_size * 69.17
        velocity = magnitude * pixel_size / (delta / 60)
    return velocity

def calculate_vel_area(magnitude, vel_unit, pixel_area, delta):
    """ 
    Calculate the velocity from an array of magnitudes given a unit of velocity.

    Parameters
    ----------
    magnitude : array-like
        The array of magnitudes, typically in pixels or other measurement units.
    vel_unit : str
        The unit of velocity to convert to. Options are 'km/h', 'm/s', or 'mp/h'.
    pixel_area : float
        The area of each pixel in kilometers.
    delta : float
        The time interval in minutes over which the magnitude was measured.

    Returns
    -------
    velocity : array-like
        The calculated velocity in the specified unit of measurement.

    Notes
    -----
    - The conversion factors used are:
        - For 'km/h': 1 pixel = 111.32 km (approximated)
        - For 'm/s': 1 pixel = 111320 meters (approximated)
        - For 'mp/h': 1 pixel = 69.17 miles (approximated)
    - delta should be provided in minutes. The formula assumes delta is the total time for the entire distance measurement.
    """
    if vel_unit == 'km/h':
        velocity = np.sqrt(magnitude * pixel_area) / (delta / 60)
    elif vel_unit == 'm/s':
        #convert km2 to m2
        pixel_area = pixel_area * 1000000
        velocity = np.sqrt(magnitude * pixel_area) / (delta * 60)
    elif vel_unit == 'mp/h':
        #convert km2 to miles2
        pixel_area = pixel_area * 0.386102
        velocity = np.sqrt(magnitude * pixel_area) / (delta / 60)
    return velocity
