Post-processing
=======================================================

After tracking, the ``pyfortracc.post_processing`` module can add information to the
tracking table and export it to other formats. All functions work on the tracking table in
``output_path + 'track/trackingtable/'`` and take the same ``name_list`` used in the tracking.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Function
     - What it does
   * - :ref:`compute_duration <BI/BI_POSTPROCESSING:Cluster duration (compute_duration)>`
     - Adds the total duration of each cluster and marks its first and last frame (``duration``, ``genesis``).
   * - :ref:`add_raster_data <BI/BI_POSTPROCESSING:Adding raster data (add_raster_data)>`
     - Extracts values or statistics from external gridded data (e.g. temperature, wind, lightning
       density) inside each cluster.
   * - :ref:`add_vector_data <BI/BI_POSTPROCESSING:Adding vector data (add_vector_data)>`
     - Labels each cluster with an attribute of a vector layer (e.g. state, basin, land cover class).
   * - :ref:`track2raster <BI/BI_POSTPROCESSING:Tracking table to raster (track2raster)>`
     - Rasterizes columns of the tracking table into NetCDF grids.
   * - :ref:`spatial_vectors <BI/BI_POSTPROCESSING:Vector fields to raster (spatial_vectors)>`
     - Rasterizes the displacement vectors (``u_``, ``v_`` and corrections) into NetCDF grids.
   * - :ref:`convert_parquet_to_family <BI/BI_POSTPROCESSING:ForTraCC family files (convert_parquet_to_family)>`
     - Exports the tracking in the classic ForTraCC "family" text format and as CSV.
   * - :ref:`pyfortracc.spatial_conversions <BI/BI_POSTPROCESSING:Geospatial export (spatial_conversions)>`
     - Exports boundaries, trajectories, vector fields and cluster masks as GeoJSON/Shapefile/NetCDF.

.. code-block:: python

    from pyfortracc.post_processing import (compute_duration, add_raster_data,
                                            add_vector_data, track2raster,
                                            spatial_vectors, convert_parquet_to_family)

.. warning::

   ``compute_duration``, ``add_raster_data`` and ``add_vector_data`` **overwrite the tracking
   table files in place**, adding new columns. Make a copy of ``output_path`` if you need to
   keep the original tables. Also, calling ``pyfortracc.track`` again (with ``clean=True``,
   the default) deletes the output folder and removes these columns.

.. note::

   All functions accept a ``parallel`` argument. As in the tracking, parallel processing uses
   ``multiprocessing``, so in scripts call the functions inside an
   ``if __name__ == '__main__':`` block. In Jupyter on macOS and Windows the functions
   automatically run in serial mode.

The examples on this page use the tracking produced in :doc:`BI_QUICKSTART`.


Cluster duration (compute_duration)
-------------------------------------------------------

The ``lifetime`` column shows how long a cluster has existed **up to each frame**. The total duration
of the cluster is only known at the end of its life. ``compute_duration`` reads the whole
tracking table (using DuckDB) and writes the total duration to every row.

.. code-block:: python

    from pyfortracc.post_processing import compute_duration

    compute_duration(name_list, parallel=True)

You can also compute it directly in the tracking call:

.. code-block:: python

    pyfortracc.track(name_list, read_function, duration=True)

New columns:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Column
     - Description
   * - ``duration``
     - Total duration of the cluster in minutes (last timestamp − first timestamp). Clusters
       observed in a single frame get ``0``.
   * - ``genesis``
     - ``1`` in the first frame of the cluster (genesis), ``-1`` in the last frame
       (dissipation) and ``0`` in between.

For multi-threshold runs the duration is computed per ``iuid``, so internal clusters get
their own duration.

Example: select the clusters that lasted at least 30 minutes, and count initiations per frame:

.. code-block:: python

    import glob
    import pandas as pd

    files = sorted(glob.glob(name_list['output_path'] + 'track/trackingtable/*.parquet'))
    tracking_table = pd.concat(pd.read_parquet(f) for f in files)

    long_lived = tracking_table[tracking_table['duration'] >= 30]
    print(long_lived['uid'].nunique(), 'clusters lasted 30 minutes or more')

    initiations = tracking_table[tracking_table['genesis'] == 1].groupby('timestamp').size()


Adding raster data (add_raster_data)
-------------------------------------------------------

``add_raster_data`` combines the tracked clusters with **other gridded datasets**. For each
cluster polygon it extracts the pixels of the external raster that fall inside the
cluster (zonal statistics), and saves the values or statistics as new columns. Typical uses
are extracting satellite brightness temperature for radar-tracked cells, reanalysis
variables (wind shear, CAPE, humidity), or land cover and topography.

The external raster does **not** need to have the same grid or resolution as the tracking
data: the extraction uses the geographic coordinates of both.

Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 24 16 60

   * - Parameter
     - Default
     - Description
   * - ``name_list``
     - *required*
     - The tracking ``name_list``. It must contain ``output_path`` and geographic bounds.
   * - ``raster_function``
     - *required*
     - Function that receives a raster file path and returns an ``xarray.DataArray`` (or
       ``Dataset``) with ``lat`` and ``lon`` dimensions **and a CRS** (see below).
   * - ``raster_path``
     - *required*
     - Folder with the raster files (all files in it are used), or the path/glob of the files.
   * - ``raster_file_pattern``
     - *required*
     - ``datetime`` pattern of the raster **file names**, used to match each raster to a
       tracking frame, e.g. ``'era5_%Y%m%d_%H.nc'``.
   * - ``merge_mode``
     - ``'nearest'``
     - How raster files are matched to tracking frames in time. ``'nearest'`` uses the
       raster closest in time to each frame.
   * - ``statistics``
     - ``None``
     - What to extract. ``None`` (or ``'pixels'``) stores the list of all pixel values inside
       the cluster. You can also pass a string or a list with ``'mean'``, ``'median'``, ``'std'``,
       ``'min'``, ``'max'``, ``'mode'``, ``'count'``, ``'values'`` or ``'percentile_X'``
       (e.g. ``'percentile_90'``).
   * - ``return_positions``
     - ``False``
     - With ``'values'``, also stores the position of each value: ``<var>_xy`` (column and row
       in the tracking grid) and ``<var>_coords`` (longitude, latitude). The raster is resampled
       to the tracking grid first. Useful with :ref:`track2raster <BI/BI_POSTPROCESSING:Tracking table to raster (track2raster)>`.
   * - ``parallel``
     - ``True``
     - Process the tracking files in parallel.

.. warning::

   In the current version only ``merge_mode='nearest'`` works. The ``'fixed'`` and
   ``'tolerance'`` modes described in the function docstring raise a ``KeyError``. To use a
   single static raster (e.g. topography), put only that file in ``raster_path`` with
   ``'nearest'``: every frame is matched to it.

   The function also fails if a tracking frame has no clusters (an empty parquet file).

The raster function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The raster function must return an ``xarray`` object with:

* dimensions named ``lat`` and ``lon`` (rename them if your file uses ``latitude``/``longitude``
  or ``y``/``x``);
* a coordinate reference system, set with `rioxarray <https://corteva.github.io/rioxarray/>`_
  (``import rioxarray`` enables the ``.rio`` accessor).

Each 2D variable (``lat``, ``lon``) of the returned object becomes a group of new columns
named after the variable.

.. code-block:: python

    import xarray as xr
    import rioxarray  # noqa: F401  (enables the .rio accessor)

    def raster_function(path):
        ds = xr.open_dataset(path)
        da = ds['temperature']                                   # select one variable
        # da = da.rename({'latitude': 'lat', 'longitude': 'lon'})  # if needed
        return da.rio.write_crs('EPSG:4326')

Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract the mean, maximum and 90th percentile of the ``temperature`` variable inside every
cluster. The raster files are named ``temp_00.nc``, ``temp_05.nc``, ... (one every 5 minutes),
and each tracking frame gets the closest file in time:

.. code-block:: python

    from pyfortracc.post_processing import add_raster_data

    if __name__ == '__main__':
        add_raster_data(name_list,
                        raster_function=raster_function,
                        raster_path='aux_raster/',
                        raster_file_pattern='temp_%M.nc',
                        merge_mode='nearest',
                        statistics=['mean', 'max', 'percentile_90'])

New columns in the tracking table:

.. code-block:: text

            temperature_mean  temperature_max  temperature_percentile_90
    cindex
    13             24.528721        49.765328                  44.061964
    14             24.775595        49.332023                  45.057657

With ``statistics=None`` a single column ``temperature`` stores the list of pixel values of
each cluster, which you can use to compute any other statistic later.


Adding vector data (add_vector_data)
-------------------------------------------------------

``add_vector_data`` intersects each cluster with the polygons of a vector file (Shapefile,
GeoPackage, GeoJSON, or any format readable by geopandas). It copies one attribute of the polygon to the
tracking table. When a cluster intersects more than one polygon, it receives the attribute
of the polygon with the **largest intersection area**. Clusters that do not intersect any
polygon get ``None``.

Typical uses: labeling clusters by country, state or municipality, river basin, biome, or
land/ocean mask.

.. list-table::
   :header-rows: 1
   :widths: 24 16 60

   * - Parameter
     - Default
     - Description
   * - ``name_list``
     - *required*
     - The tracking ``name_list``.
   * - ``vector_path``
     - *required*
     - Path to a vector file, or to a folder with several vector files.
   * - ``vector_column``
     - *required*
     - Attribute of the vector file to copy.
   * - ``track_column``
     - ``None``
     - Name of the new column in the tracking table. Uses ``vector_column`` if ``None``.
   * - ``merge_mode``
     - ``'fixed'``
     - ``'fixed'`` uses the same (first) vector file for every frame. ``'nearest'`` and
       ``'tolerance'`` match time-varying vector files by their file names.
   * - ``vector_file_pattern``
     - ``None``
     - ``datetime`` pattern of the vector file names; required for ``'nearest'`` and ``'tolerance'``.
   * - ``time_tolerance``
     - ``None``
     - Maximum time difference for ``'tolerance'`` mode (e.g. ``'1h'``, ``'1D'``). Frames
       without a vector file within the tolerance are not labeled.
   * - ``parallel``
     - ``True``
     - Process the tracking files in parallel.

.. warning::

   In the current version only ``merge_mode='fixed'`` works; ``'nearest'`` and ``'tolerance'``
   raise a ``KeyError``. Use a single, static vector file.

.. important::

   The vector file must use the **same coordinates as the tracking geometries**: longitude and
   latitude (EPSG:4326) when the ``name_list`` has geographic bounds. Reproject it first if needed:
   ``gpd.read_file(path).to_crs('EPSG:4326').to_file('regions_4326.gpkg')``.

Example:

.. code-block:: python

    import geopandas as gpd
    from shapely.geometry import box
    from pyfortracc.post_processing import add_vector_data

    # A simple vector file with two regions
    regions = gpd.GeoDataFrame({'region': ['West', 'East']},
                               geometry=[box(-60, -5, -57.5, 0), box(-57.5, -5, -55, 0)],
                               crs='EPSG:4326')
    regions.to_file('regions.geojson', driver='GeoJSON')

    if __name__ == '__main__':
        add_vector_data(name_list,
                        vector_path='regions.geojson',
                        vector_column='region')

    # Number of clusters per region
    tracking_table = pd.concat(pd.read_parquet(f) for f in files)
    print(tracking_table.groupby('region')['uid'].nunique())


Tracking table to raster (track2raster)
-------------------------------------------------------

``track2raster`` converts columns of the tracking table into gridded fields. For every
frame, each cluster polygon is filled with the value of the chosen column, producing
maps such as "lifetime of the system at each pixel" or "mean temperature of the system at
each pixel". Grids are easier to combine with other gridded data and to use for climatologies.

.. code-block:: python

    from pyfortracc.post_processing import track2raster

    track2raster(name_list, read_function,
                 columns=['size', 'lifetime', 'temperature_mean'],
                 parallel=False)

* ``columns``: list of numeric columns to rasterize. If ``None``, all ``u_*`` and ``v_*``
  columns are used. The ``opt_field`` column (optical flow vectors) is converted to
  ``u_opt_field`` and ``v_opt_field``. A ``<var>_values`` column created by
  ``add_raster_data(..., statistics='values', return_positions=True)`` is written pixel by
  pixel using the ``<var>_xy`` positions.
* Output: one NetCDF per frame in ``output_path + 'track/raster/'`` with dimensions
  ``(time, threshold_level, lat, lon)`` (or ``y``, ``x`` without geographic bounds). Pixels
  outside the clusters are ``NaN``.

.. code-block:: python

    import xarray as xr

    ds = xr.open_mfdataset(name_list['output_path'] + 'track/raster/*.nc')
    # Maximum lifetime observed at each pixel over the whole period
    ds['lifetime'].isel(threshold_level=0).max('time').plot()


Vector fields to raster (spatial_vectors)
-------------------------------------------------------

``spatial_vectors`` writes the displacement vectors of all methods (``u_``/``v_``,
``u_spl``/``v_spl``, ``u_opt``/``v_opt``, ...) as gridded fields. Each vector is placed on the
pixels of its cluster (with geographic bounds) or on the cluster centroid (without them).
For the optical flow method, the individual flow vectors of ``opt_field`` are also included.

.. code-block:: python

    from pyfortracc.post_processing import spatial_vectors

    spatial_vectors(name_list, read_function, parallel=False)

Output: one NetCDF per frame in ``output_path + 'track/spatial_vectors/'`` with variables
``u_<method>`` and ``v_<method>`` and dimensions ``(time, threshold_level, lat, lon)``. Frames
without any valid vector are skipped.


ForTraCC family files (convert_parquet_to_family)
-------------------------------------------------------

``convert_parquet_to_family`` exports the tracking in the text format of the original
ForTraCC algorithm, in which each cluster (*family*) is written as a block. This makes it
easy to reuse legacy scripts written for ForTraCC.

.. code-block:: python

    from pyfortracc.post_processing import convert_parquet_to_family

    convert_parquet_to_family(name_list, csv_out=True)

* Only the first threshold (``threshold_level == 0``) is exported.
* Files are written to ``output_path + 'track/family/'`` and named
  ``family_<first time>_<last time>`` (``%Y%m%d%H``), with extensions ``.txt`` and, if
  ``csv_out=True``, ``.csv`` (separator ``;``).
* Missing values (e.g. the vector of a ``NEW`` cluster) are written as ``-999.99``
  (``default_undef`` argument).

Example of the ``.txt`` file:

.. code-block:: text

    FAMILY= 1.0 - YEAR=1900 MONTH=1 DAY=1 HOUR=0.00
             uid   cluster_id         time         clat         clon         size    expansion          dir           u_           v_       status
            1.00         1.00         0.02        -0.74       -56.53       140.00      -999.99      -999.99      -999.99      -999.99          NEW
            1.00         1.00         0.03        -0.82       -56.61       166.00      2832.24       226.88        -0.08        -0.08          CON
    ...
    TOTAL TIME= 0.47

Columns: ``time`` is the lifetime in hours, ``clat``/``clon`` the centroid, ``dir`` the
direction of movement in degrees computed from ``u_`` and ``v_``, and ``TOTAL TIME`` the
duration of the family in hours.


Geospatial export (spatial_conversions)
-------------------------------------------------------

``pyfortracc.spatial_conversions`` exports the tracking to standard geospatial formats that can be
opened in GIS software. It requires the geographic bounds (``lon_min``, ``lon_max``,
``lat_min``, ``lat_max``) in the ``name_list``.

.. code-block:: python

    pyfortracc.spatial_conversions(name_list, read_function,
                                   boundary=True,       # cluster polygons
                                   trajectory=True,     # trajectory lines
                                   vector_field=False,  # optical flow vectors (needs opt_correction)
                                   cluster=True,        # cluster masks as NetCDF
                                   start_time=None,     # e.g. '2014-08-16 10:00:00'
                                   end_time=None,
                                   vel_unit='km/h',
                                   driver='GeoJSON')    # or 'ESRI Shapefile', 'GPKG'

.. list-table::
   :header-rows: 1
   :widths: 22 38 40

   * - Option
     - Output folder
     - Content
   * - ``boundary``
     - ``track/geometry/boundary/``
     - Cluster polygons with their attributes, one file per frame.
   * - ``trajectory``
     - ``track/geometry/trajectory/``
     - Trajectory lines of the clusters, one file per frame.
   * - ``vector_field``
     - ``track/geometry/vector_field/``
     - Optical flow vectors (only when tracking with ``opt_correction = True``).
   * - ``cluster``
     - ``track/clusters/``
     - NetCDF with a ``Clusters`` variable (the ``uid`` of each cluster on the grid), one file per frame.
       Requires ``save_arrays = True`` during the tracking.

``start_time`` and ``end_time`` limit the export to a period.
