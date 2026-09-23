Name List
========================================================

The **name list** is a Python dictionary with all the parameters of a pyForTraCC run. The same
dictionary is passed to ``track``, ``forecast``, the plotting functions and the post-processing
functions.

Only a few keys are mandatory. Every other key has a default value, filled in by
``pyfortracc.default_parameters`` when a run starts. To see the defaults, call it on your
dictionary:

.. code-block:: python

    import pyfortracc
    full_name_list = pyfortracc.default_parameters(dict(name_list), read_function)

or read the file ``pyfortracc/default_parameters.py``.


Mandatory parameters
--------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 22 14 64

   * - Key
     - Type
     - Description
   * - ``input_path``
     - str
     - Folder with the input files. All files in the folder **and its subfolders** are read, so
       keep only input data in it. End the path with ``/``.
   * - ``output_path``
     - str
     - Folder where the results are written. End the path with ``/``. By default it is
       **deleted** at the start of ``track`` (see ``clean`` in :doc:`BI_TRACKING`).
   * - ``thresholds``
     - list
     - Intensity thresholds used to segment the field, e.g. ``[20, 30, 40]`` dBZ. Order them
       from the least to the most intense (for ``'<='``, e.g. brightness temperature, from the
       warmest to the coldest: ``[235, 220, 210]``). Each threshold is a *threshold level*
       (0, 1, 2, ...).
   * - ``min_cluster_size``
     - list
     - Minimum number of pixels of a cluster, one value per threshold, e.g. ``[10, 5, 3]``.
       Smaller clusters are discarded.
   * - ``operator``
     - str
     - Comparison used for the segmentation: ``'>='``, ``'>'``, ``'<='``, ``'<'``, ``'=='``
       or ``'!='``. Use ``'>='`` for reflectivity or precipitation, ``'<='`` for infrared
       brightness temperature, and ``'=='`` for categorical maps.
   * - ``timestamp_pattern``
     - str or list
     - ``datetime`` format of the file names, used to get the time of each file, e.g.
       ``'%Y%m%d_%H%M%S.nc'``. See :ref:`Timestamps from file names <BI/BI_DATA:Timestamps from file names>`.
   * - ``delta_time``
     - int/float
     - Expected interval between consecutive files, in **minutes** (e.g. ``10``; one year is
       ``525960``).

.. code-block:: python

    name_list = {}
    name_list['input_path'] = 'input/'                   # path to the input data
    name_list['output_path'] = 'output/'                 # path to the output data
    name_list['thresholds'] = [20, 30, 40]               # dBZ
    name_list['min_cluster_size'] = [10, 5, 3]           # pixels, one per threshold
    name_list['operator'] = '>='                         # segmentation operator
    name_list['timestamp_pattern'] = '%Y%m%d_%H%M%S.nc'  # file name pattern
    name_list['delta_time'] = 12                         # minutes


Geographic parameters
--------------------------------------------------------

Without these keys, the tracking works in **pixel coordinates**: geometries, trajectories and
vectors are given in pixels. With them, pyForTraCC uses longitude/latitude. They are required
for the forecast, geospatial exports and map plots.

.. list-table::
   :header-rows: 1
   :widths: 22 14 64

   * - Key
     - Default
     - Description
   * - ``lon_min``, ``lon_max``
     - ``None``
     - Longitude of the western and eastern edges of the grid, in degrees.
   * - ``lat_min``, ``lat_max``
     - ``None``
     - Latitude of the southern and northern edges of the grid, in degrees.
   * - ``x_dim``, ``y_dim``
     - from data
     - Number of columns (x) and rows (y) of the grid. If not given, they are read from the
       shape of the first input file.

The pixel resolution is computed as ``(lon_max - lon_min) / x_dim`` and
``(lat_max - lat_min) / y_dim``. Row 0 of the array is assumed to be at ``lat_min``
(south). If your array starts in the north, flip it in the read function
(``data[::-1, :]``); see :doc:`BI_DATA`.

.. code-block:: python

    name_list['lon_min'] = -62.1475
    name_list['lon_max'] = -57.8461
    name_list['lat_min'] = -5.3048
    name_list['lat_max'] = -0.9912


Segmentation and clustering
--------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 22 14 64

   * - Key
     - Default
     - Description
   * - ``cluster_method``
     - ``'ndimage'``
     - ``'ndimage'``: connected pixels (fast, recommended). ``'dbscan'``: DBSCAN clustering
       from scikit-learn (slower), which can join pixels that are close but not touching.
   * - ``eps``
     - ``1``
     - Maximum distance (in pixels) between two pixels of the same cluster, used by
       ``'dbscan'``.
   * - ``convex_hull``
     - ``False``
     - Use the convex hull of each cluster as its geometry.
   * - ``save_arrays``
     - ``True``
     - Save the pixels of each cluster (``array_x``, ``array_y``, ``array_values`` columns).
       Setting ``False`` reduces disk and memory use a lot for large domains. It **cannot**
       be combined with ``opt_correction`` or ``validation`` (an error is raised). Without these
       columns the forecast cannot be run, and cluster masks are not exported. ``plot``
       then needs a ``read_function``.


Linking in time
--------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 22 14 64

   * - Key
     - Default
     - Description
   * - ``min_overlap``
     - ``10``
     - Minimum overlap, in **percent of the area of the previous cluster**, for two clusters in
       consecutive frames to be linked. Increase it to avoid wrong links in dense fields.
       Decrease it for small or fast clusters.
   * - ``delta_tolerance``
     - ``0``
     - Extra time (minutes) accepted between two frames. Files arriving up to
       ``delta_time + delta_tolerance`` after the previous one are still linked. Useful when the
       data interval is irregular.
   * - ``num_prev_skip``
     - ``0``
     - Number of previous files to skip when searching for the previous frame (advanced). To
       link across data gaps, ``delta_tolerance`` must also cover the size of the gap.
   * - ``edges``
     - ``False``
     - Link clusters that cross the left/right border of the domain. Use it for global data
       where longitude wraps around (e.g. −180°/180°).
   * - ``preserv_split``
     - ``False``
     - Clusters created by a split (``NEW/SPL``) inherit the lifetime of the parent cluster
       instead of starting from ``delta_time``.
   * - ``prv_uid``
     - ``False``
     - Add the columns ``prv_mrg_uids``, ``prv_mrg_iuids``, ``prv_spl_uid`` and ``prv_spl_iuid``.
       They list the uids that took part in merges and splits, so you can reconstruct the
       family tree of the clusters.
   * - ``initial_uid``
     - ``1``
     - First ``uid`` given to new clusters.


Vector corrections
--------------------------------------------------------

The displacement vector of a cluster (``u_``, ``v_``) is the shift of its centroid between two
frames. It can be distorted when a cluster changes shape, splits or merges. The methods below
compute alternative vectors, stored in separate columns. See :doc:`BI_TRACKING`
and the :doc:`vector correction methods <../CF/CORRECTION>` page.

.. list-table::
   :header-rows: 1
   :widths: 22 14 64

   * - Key
     - Default
     - Description
   * - ``spl_correction``
     - ``False``
     - Correction for split events (``u_spl``, ``v_spl``).
   * - ``mrg_correction``
     - ``False``
     - Correction for merge events (``u_mrg``, ``v_mrg``).
   * - ``inc_correction``
     - ``False``
     - Correction using the inner cores, i.e. the clusters of higher thresholds inside each
       cluster (``u_inc``, ``v_inc``). Requires more than one threshold.
   * - ``opt_correction``
     - ``False``
     - Correction using optical flow (``u_opt``, ``v_opt`` and the flow vectors in
       ``opt_field``). Requires ``save_arrays = True``.
   * - ``opt_mtd``
     - ``'lucas-kanade'``
     - Optical flow algorithm: ``'lucas-kanade'`` or ``'farneback'``.
   * - ``elp_correction``
     - ``False``
     - Correction using the centroids of ellipses fitted to the clusters (``u_elp``, ``v_elp``).
   * - ``new_correction``
     - ``False``
     - Estimates a vector for ``NEW`` clusters, which have no previous match and therefore no
       vector. It uses the mean of the vectors of the nearest clusters (``u_new``, ``v_new``). The
       estimate is also written to ``u_``/``v_``.
   * - ``new_neighbors``
     - ``3``
     - Number of nearest clusters used by ``new_correction``.
   * - ``validation``
     - ``False``
     - Chooses the best vector for each cluster. The previous cluster is extrapolated with each
       method, and the method with the lowest false alarm ratio against the current cluster is
       selected. The chosen vector is written to ``u_``/``v_``, the method name to ``method``
       and its score to ``far``. Requires ``save_arrays = True``.
   * - ``validation_scores``
     - ``False``
     - Also save the scores of every method (``hit_<m>``, ``false-alarm_<m>``, ``far_<m>``) and
       the original vector (``u_noc``, ``v_noc``).
   * - ``mrg_expansion``, ``spl_expansion``
     - ``False``
     - Take merges/splits into account when computing the ``expansion`` rate.

Example: enable all corrections and choose the best one automatically.

.. code-block:: python

    name_list['spl_correction'] = True
    name_list['mrg_correction'] = True
    name_list['inc_correction'] = True
    name_list['opt_correction'] = True
    name_list['opt_mtd'] = 'farneback'
    name_list['elp_correction'] = True
    name_list['new_correction'] = True
    name_list['validation'] = True


Forecast parameters
--------------------------------------------------------

Used only by ``pyfortracc.forecast``. See :doc:`BI_FORECAST`.

.. list-table::
   :header-rows: 1
   :widths: 22 14 64

   * - Key
     - Default
     - Description
   * - ``forecast_time``
     - ``None``
     - Issue time of the forecast, ``'YYYY-MM-DD HH:MM:SS'``.
   * - ``observation_window``
     - ``None``
     - Number of past frames used to compute the mean motion.
   * - ``lead_time``
     - ``None``
     - Number of time steps to forecast.
   * - ``forecast_mode``
     - ``'persistence'``
     - Forecast method. Only ``'persistence'`` is available.


Execution parameters
--------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 22 14 64

   * - Key
     - Default
     - Description
   * - ``n_jobs``
     - ``-1``
     - Number of parallel processes. ``-1`` uses all CPU cores. Reduce it if you run out of
       memory.
   * - ``resume``
     - ``False``
     - Resume an interrupted run (see :ref:`Resuming an interrupted run <BI/BI_TRACKING:Resuming an interrupted run>`). When using
       ``track``, pass ``resume=True`` to the function instead; the argument overrides
       this key.
   * - ``pattern_position``
     - ``[None, None]``
     - Slice ``[start, end]`` of the file name that contains the date. Use it when the file name has
       other variable parts. See :ref:`Timestamps from file names <BI/BI_DATA:Timestamps from file names>`.
   * - ``default_columns``
     - ``True``
     - Keep only the standard columns in the tracking table.


Complete example
--------------------------------------------------------

Tracking of radar reflectivity with three thresholds, DBSCAN clustering, geographic bounds and
vector corrections:

.. code-block:: python

    name_list = {}
    # Mandatory
    name_list['input_path'] = 'input/'
    name_list['output_path'] = 'output/'
    name_list['timestamp_pattern'] = 'sbmn_cappi_%Y%m%d_%H%M.nc.gz'
    name_list['thresholds'] = [20, 30, 35]
    name_list['min_cluster_size'] = [3, 3, 3]
    name_list['operator'] = '>='
    name_list['delta_time'] = 12
    # Clustering and linking
    name_list['cluster_method'] = 'dbscan'
    name_list['min_overlap'] = 20
    name_list['delta_tolerance'] = 2
    # Geographic bounds
    name_list['lon_min'] = -62.1475
    name_list['lon_max'] = -57.8461
    name_list['lat_min'] = -5.3048
    name_list['lat_max'] = -0.9912
    # Vector corrections
    name_list['spl_correction'] = True
    name_list['mrg_correction'] = True
    name_list['inc_correction'] = True
    name_list['opt_correction'] = True
    name_list['validation'] = True
