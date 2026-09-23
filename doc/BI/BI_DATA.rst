Data Input
=======================================================

pyForTraCC does not depend on a specific variable, sensor or file format. Radar reflectivity,
satellite brightness temperature, precipitation estimates, land cover maps and synthetic
images are all tracked the same way. What the library needs is:

1. a **folder of files**, one file per time step;
2. a **timestamp in each file name**, described by ``timestamp_pattern``;
3. a **read function** that opens one file and returns a 2D ``numpy`` array.


The read function
--------------------------------------------------------

The read function is a Python function written by you. It receives the path of a single file and
returns a two-dimensional ``numpy`` array with shape ``(rows, columns)``, i.e.
``(latitude, longitude)``:

.. code-block:: python

    import xarray as xr

    def read_function(path):
        return xr.open_dataarray(path).data

pyForTraCC calls this function for every file in ``input_path`` (in parallel), so it is where you:

* select the variable, vertical level or band;
* crop the region of interest;
* convert units (e.g. scale factors, Kelvin);
* replace fill values with ``np.nan``;
* flip the array so that the first row is the **southernmost** one.

Rules for the returned array:

* It must be 2D, and all files must have the **same shape**.
* Missing values must be ``np.nan`` (e.g. ``data[data == -9999] = np.nan``).
* Row 0 is assumed to be at ``lat_min``. Many datasets store the northernmost row first. In that case
  return ``data[::-1, :]``, otherwise the geographic coordinates of the clusters will be
  mirrored.

Always test your function on one file before tracking:

.. code-block:: python

    import glob
    import numpy as np

    files = sorted(glob.glob('input/*.nc'))
    sample = read_function(files[0])
    print(sample.shape, sample.dtype, np.nanmin(sample), np.nanmax(sample))

    # Quick look at the input files (Jupyter)
    import pyfortracc
    pyfortracc.plot_animation(path_files='input/*.nc', read_function=read_function,
                              num_frames=10)

Examples of read functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**NetCDF with several variables** (e.g. GOES-16 infrared, cropped to a region):

.. code-block:: python

    import xarray as xr

    def read_function(path):
        ds = xr.open_dataset(path)
        ds = ds.sel(lon=slice(-75, -41), lat=slice(-12, 8))   # crop the region
        return ds['Band1'].data / 100                          # scale to Kelvin

**Compressed NetCDF (.gz) with vertical levels** (e.g. radar CAPPI):

.. code-block:: python

    import gzip
    import netCDF4
    import numpy as np

    def read_function(path):
        with gzip.open(path) as gz:
            with netCDF4.Dataset('dummy', mode='r', memory=gz.read()) as nc:
                data = nc.variables['DBZc'][:].data[0, 5, :, :]   # time 0, level 5 (2.5 km)
        data[data == -9999] = np.nan                               # fill value -> NaN
        return data[::-1, :]                                      # north-up -> south-up

**GeoTIFF with categories** (e.g. MapBiomas land cover, tracking anthropogenic areas):

.. code-block:: python

    import numpy as np
    import rasterio

    def read_function(path):
        with rasterio.open(path) as src:
            data = src.read(1)[::-1]
        anthropic_classes = [14, 15, 18, 19, 39, 20, 40, 62, 41, 36, 46, 47, 48, 9, 21]
        return np.where(np.isin(data, anthropic_classes), 1, 0)   # use operator '=='

**Images (PNG/JPG)**:

.. code-block:: python

    import numpy as np
    from PIL import Image

    def read_function(path):
        img = np.array(Image.open(path).convert('L')).astype(float)
        return np.where(img < 250, 1.0, 0.0)


Timestamps from file names
--------------------------------------------------------

The time of each file is read from its **file name** (not from the file contents), using the
``timestamp_pattern`` key. It is a pattern with the
`datetime format codes <https://docs.python.org/3/library/datetime.html#format-codes>`_:
``%Y`` year, ``%m`` month, ``%d`` day, ``%j`` day of year, ``%H`` hour, ``%M`` minute, ``%S``
second. The pattern must match the **whole** file name, including the fixed text and the
extension:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - File name
     - ``timestamp_pattern``
   * - ``20140212_101200.nc``
     - ``'%Y%m%d_%H%M%S.nc'``
   * - ``sbmn_cappi_20140816_1012.nc.gz``
     - ``'sbmn_cappi_%Y%m%d_%H%M.nc.gz'``
   * - ``S10635346_202202010000.nc``
     - ``'S10635346_%Y%m%d%H%M.nc'``
   * - ``RRQPE-INST-GLB_v1r1_blend_s202201010000000.nc``
     - ``'RRQPE-INST-GLB_v1r1_blend_s%Y%m%d%H%M%S0.nc'``
   * - ``1985.tif``
     - ``'%Y.tif'``

Test the pattern with Python before tracking:

.. code-block:: python

    from datetime import datetime
    datetime.strptime('sbmn_cappi_20140816_1012.nc.gz', 'sbmn_cappi_%Y%m%d_%H%M.nc.gz')

**Several naming conventions.** If the file names change during the period (e.g. a new
product version), give a list of patterns. The first one that matches is used:

.. code-block:: python

    name_list['timestamp_pattern'] = ['gsmap_mvk.%Y%m%d.%H%M.v8.0000.0.nc',
                                      'gsmap_mvk.%Y%m%d.%H%M.v8.0000.1.nc']

**Variable parts in the name.** If the file name contains parts that change and are not a
date (e.g. a processing time, ``OR_ABI-L2-CMIPF-M6C13_G16_s20223001200205_e20223001209513_c20223001209584.nc``),
use ``pattern_position`` to keep only the slice of the name with the date. The slice follows
Python string indexing ``[start:end]``:

.. code-block:: python

    name = 'OR_ABI-L2-CMIPF-M6C13_G16_s20223001200205_e20223001209513_c20223001209584.nc'
    print(name[27:38])                               # '20223001200'

    name_list['pattern_position'] = [27, 38]
    name_list['timestamp_pattern'] = '%Y%j%H%M'      # year, day of year, hour, minute

.. note::

   Only dates are stored in the output file names (``%Y%m%d_%H%M.parquet``), so each input file
   must correspond to a different minute.


Organizing the input folder
--------------------------------------------------------

* All files inside ``input_path`` **and its subfolders** are used, sorted by name. Do not keep
  other files (logs, figures, ``.zip``) in this folder.
* Files that cannot be read (the read function raises an error) are reported and treated as
  frames without clusters.
* Time gaps larger than ``delta_time + delta_tolerance`` break the trajectories: clusters after
  the gap start again as ``NEW``.
* The folders can be organized by date, e.g. ``input/2014/08/16/*.nc``.
