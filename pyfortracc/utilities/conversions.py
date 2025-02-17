import numpy as np

def dbz2mm6m3(dBZ_array):
    """ 
    Convert radar reflectivity (dBZ) to the unit of mm^6/m^3.

    Parameters
    ----------
    dBZ_array : array-like
        An array of reflectivity values in dBZ (decibels of Z), which is a logarithmic measure of radar reflectivity.

    Returns
    -------
    mm6m3_values : array-like
        The converted reflectivity values in mm^6/m^3, representing the volume concentration of hydrometeors.

    Notes
    -----
    - The conversion formula used is: mm^6/m^3 = 10^(dBZ/10)
    - This conversion assumes that dBZ is a logarithmic measurement of the reflectivity factor (Z) in mm^6/m^3.
    """
    mm6m3_values = 10.0 ** (dBZ_array / 10.0) # Convert reflectivity to mm^6/m^3
    return mm6m3_values


def mm6m32dbz(mm6m3_array):
    """ 
    Convert volume concentration of hydrometeors from mm^6/m^3 to radar reflectivity in dBZ.

    Parameters
    ----------
    mm6m3_array : array-like
        An array of reflectivity values in units of mm^6/m^3, representing the volume concentration of hydrometeors.

    Returns
    -------
    dBZ_array : array-like
        The converted reflectivity values in decibels of Z (dBZ), which is a logarithmic measure of radar reflectivity.

    Notes
    -----
    - The conversion formula used is: dBZ = 10 * log10(mm^6/m^3)
    - This conversion assumes that the input values are in mm^6/m^3, and converts them to the logarithmic dBZ scale used in radar meteorology.
    """
    dBZ_array = 10.0 * np.log10(mm6m3_array) # Convert mm^6/m^3 to dBZ
    return dBZ_array


def dbz2mmh(dBZ_array, a=200.0, b=1.6):
    """ 
    Convert radar reflectivity in dBZ to rainfall rate in mm/h using the Marshall-Palmer formula.

    Parameters
    ----------
    dBZ_array : array-like
        An array of reflectivity values in decibels (dBZ). This represents radar reflectivity on a logarithmic scale.
    a : float, optional
        The scaling factor in the Marshall-Palmer formula. Default is 200.
    b : float, optional
        The exponent in the Marshall-Palmer formula. Default is 1.6.

    Returns
    -------
    R : array-like
        The calculated rainfall rate in millimeters per hour (mm/h).

    Notes
    -----
    - The Marshall-Palmer formula used is: R = (Z / a)^(1/b), where Z is the reflectivity factor in mm^6/m^3.
    - The conversion assumes that the dBZ values are converted to linear reflectivity first, and then the Marshall-Palmer relationship is applied to estimate the rainfall rate.
    """
    Z = 10.0 ** (dBZ_array / 10.0) # Convert reflectivity to mm^6/m^3
    R = (Z / a) ** (1.0 / b) # Apply Marshall-Palmer formula
    return R


def mmh2dbz(mmh_array, a=200.0, b=1.6):
    """ 
    Convert rainfall rate in mm/h to radar reflectivity in dBZ using the Marshall-Palmer formula.

    Parameters
    ----------
    mmh_array : array-like
        An array of rainfall rates in millimeters per hour (mm/h).
    a : float, optional
        The scaling factor used in the Marshall-Palmer formula. Default is 200.
    b : float, optional
        The exponent used in the Marshall-Palmer formula. Default is 1.6.

    Returns
    -------
    dBZ_array : array-like
        The converted reflectivity values in decibels (dBZ), which is a logarithmic measure of radar reflectivity.

    Notes
    -----
    - The Marshall-Palmer formula used is: Z = a * R^b, where Z is the reflectivity factor in mm^6/m^3 and R is the rainfall rate in mm/h.
    - After computing the reflectivity factor Z, the formula converts it to dBZ using the equation: dBZ = 10 * log10(Z).
    - The conversion assumes that the input values are in mm/h and converts them to the logarithmic dBZ scale used in radar meteorology.
    """
    Z = a * mmh_array**b # Convert mm/h to mm^6/m^3
    dBZ_array = 10.0 * np.log10(Z) # Convert mm^6/m^3 to dBZ
    return dBZ_array