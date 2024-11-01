Data Input
=======================================================
The **pyForTraCC** package supports several data formats and sources, allowing users to perform detailed hydrological feature tracking across multiple 
types of radar and satellite datasets. This section provides an overview of the compatible data formats and supported input types.

Data format
--------------------------------------------------------
The primary data input for **pyForTraCC** is a two-dimensional NumPy array, formatted with dimensions (latitude, longitude). This structure is essential 
for spatial operations and ensures compatibility with various data types.

For example, the following Python code demonstrates how to read NetCDF data into a 2D NumPy array using xarray:

.. code-block:: python

    import numpy as np
    import glob
    import xarray as xr

    def read_function(path):
        data = xr.open_dataarray(path).data
        return data

    # We use the ``glob`` module, which is useful for finding all files with the ``.nc`` extension.
    files = sorted(glob.glob('input/*.nc'))
    # We applied the function ``read_functionread_function`` to first file in liist ``file``.
    sample_data = read_function(files[0])


The ``sample_data`` variable is now a 2D ``numpy.ndarray`` ready for input into **pyForTraCC**. For further usage details, refer to the Examples section.

Satellite products
--------------------------------------------------------
The **pyForTraCC** package is compatible with various data sources, enabling tracking and analysis of hydrological features across different datasets. 
Supported input data types include:

    - **NetCDF Format**: The dataset for some examples consists of files in the NetCDF format. This data is a synthetic set created to simulate the movement of cells in a 2D domain, with each cell's values representing reflectivity, akin to radar reflectivity.

    - **Radar Data**: The S-Band Radar located in Manaus, AM, Brazil. The data, processed and published by Schumacher, Courtney, and Funk, Aaron (2018), is available in full on the ARM platform. It is part of the GoAmazon2014/5 project and is titled "Three-dimensional Gridded S-band Reflectivity and Radial Velocity from the SIPAM Manaus S-band Radar dataset."

    - **GOES-16 Satellite Data**: The GOES-16 satellite data from Channel 13 represents infrared channel information, which has been reprojected onto a rectangular grid over South America. This reprocessing ensures the data is more accessible for various applications, including weather forecasting and environmental monitoring.

    - **Global Precipitation System**: This input utilizes JAXA's Global Satellite Mapping of Precipitation (GSMAP) data, which provides precipitation estimates across the globe.

    - **SCaMPR Rainfall Rate Product**: The Self-Calibrating Multivariate Precipitation Retrieval (SCaMPR) rainfall rate product (RRQPE) is available every 10 minutes and covers the entire Earth.

These diverse datasets enable users to leverage the capabilities of the **pyForTraCC** package effectively, allowing for comprehensive 
tracking and analysis of hydrological features.
