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
    # We apply the function ``read_function`` to first file in list ``files``.
    sample_data = read_function(files[0])


