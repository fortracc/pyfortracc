Quick Start
=======================================================

This page walks through a complete pyForTraCC workflow in a few minutes:
**generate data → track → inspect → visualize → forecast → post-process**.
It uses a small synthetic dataset created by pyForTraCC itself, so no download is needed.
Every step links to the page with more details.

.. code-block:: text

    input files ──► read_function ──► track() ──► tracking table ──┬──► plot / plot_animation
                                                                   ├──► forecast()
                                                                   └──► post_processing / spatial_conversions


1. Install and import
-------------------------------------------------------

.. code-block:: console

    pip install pyfortracc

.. code-block:: python

    import pyfortracc
    print(pyfortracc.__version__)

See :doc:`BI_INSTALL` for conda and development installs.


2. Input data
-------------------------------------------------------

``bubble_simulation`` writes 30 PNG images (``frame_00.png`` ... ``frame_29.png``), one per
minute. They show a "bubble" that moves from the bottom-right to the top-left of a
50 × 50 grid, splits into two, merges back and fades away. This is a small case with the main events
the tracking must handle.

.. code-block:: python

    pyfortracc.utilities.bubble_simulation(dir='input/')

pyForTraCC reads your files with a **read function** that you write. It receives the path of a
file and must return a 2D ``numpy`` array. Here we convert each PNG into a binary field:
``1`` inside the bubbles, ``0`` outside.

.. code-block:: python

    import numpy as np
    from PIL import Image

    def read_function(path):
        img = np.array(Image.open(path).convert('L')).astype(float)
        return np.where(img < 250, 1.0, 0.0)

    print(read_function('input/frame_00.png').shape)   # (50, 50)

    # Preview the input files as an animation (Jupyter)
    pyfortracc.plot_animation(path_files='input/*.png', read_function=read_function)

See :doc:`BI_DATA` for read functions for NetCDF, GeoTIFF and compressed radar files.


3. Configure the tracking (name_list)
-------------------------------------------------------

All options are given in a Python dictionary, the ``name_list``:

.. code-block:: python

    name_list = {
        'input_path': 'input/',               # folder with the input files
        'output_path': 'output/',             # where results are written
        'thresholds': [1],                    # segmentation threshold(s)
        'min_cluster_size': [3],              # minimum cluster size (pixels) per threshold
        'operator': '>=',                     # cluster = pixels >= threshold
        'timestamp_pattern': 'frame_%M.png',  # how to read the time from the file name
        'delta_time': 1,                      # minutes between files
        # Optional: geographic bounds of the grid
        'lon_min': -60.0, 'lon_max': -55.0,
        'lat_min': -5.0,  'lat_max': 0.0,
    }

See :doc:`BI_NAMELIST` for all options.


4. Run the tracking
-------------------------------------------------------

.. code-block:: python

    if __name__ == '__main__':
        pyfortracc.track(name_list, read_function)

.. important::

   The tracking uses ``multiprocessing``. In a Python script, always call pyForTraCC functions
   inside an ``if __name__ == '__main__':`` block. In Jupyter on macOS/Windows, parallel
   processing is disabled automatically.

The tracking runs four steps (features extraction, spatial operations, cluster linking
and concatenation) and writes the **tracking table** to ``output/track/trackingtable/``,
one parquet file per time step.


5. Explore the tracking table
-------------------------------------------------------

.. code-block:: python

    import glob
    import pandas as pd

    files = sorted(glob.glob(name_list['output_path'] + 'track/trackingtable/*.parquet'))
    tracking_table = pd.concat(pd.read_parquet(f) for f in files)

    print(tracking_table[['timestamp', 'uid', 'status', 'size', 'lifetime', 'u_', 'v_']])

.. code-block:: text

                     timestamp  uid   status   size  lifetime        u_        v_
    cindex
    1      1900-01-01 00:00:00  1.0      NEW  140.0       1.0       NaN       NaN
    2      1900-01-01 00:01:00  1.0      CON  166.0       2.0 -0.079372 -0.084768
    ...
    9      1900-01-01 00:08:00  1.0      SPL  121.0       9.0 -0.256288 -0.218798
    10     1900-01-01 00:08:00  2.0  NEW/SPL   25.0       1.0       NaN       NaN
    ...
    33     1900-01-01 00:20:00  1.0      MRG  146.0      21.0  0.112753  0.316438

Each row is one cluster at one time. How to read it:

* ``uid`` identifies a cluster throughout its life. The bubble is ``uid = 1``. At 00:08 it
  splits (``SPL``), and the new piece receives ``uid = 2`` with status ``NEW/SPL``. At 00:20 they merge
  (``MRG``) back into ``uid = 1``.
* ``lifetime`` is the age of the cluster in minutes; ``size`` its area in pixels.
* ``u_`` and ``v_`` are the displacement since the previous time step, in the units of the grid
  (here degrees per time step).

Follow a single cluster:

.. code-block:: python

    cluster = tracking_table[tracking_table['uid'] == 1]
    cluster.plot(x='timestamp', y='size', marker='o', title='Size of cluster uid=1')

See :doc:`BI_TRACKING` for the description of every column.


6. Visualize
-------------------------------------------------------

.. code-block:: python

    # One time step
    pyfortracc.plot(name_list, read_function, timestamp='1900-01-01 00:10:00',
                    info_cols=['uid', 'status'])

    # Animation over a period (Jupyter)
    pyfortracc.plot_animation(name_list=name_list, read_function=read_function,
                              start_timestamp='1900-01-01 00:00:00',
                              end_timestamp='1900-01-01 00:29:00',
                              info_cols=['uid', 'lifetime', 'status'])

See :doc:`BI_UTILITIES` for all plotting options.


7. Forecast
-------------------------------------------------------

Extrapolate the clusters observed at 00:15 for the next 3 minutes, using their mean motion
over the last 3 frames:

.. code-block:: python

    if __name__ == '__main__':
        name_list['forecast_time'] = '1900-01-01 00:15:00'
        name_list['observation_window'] = 3
        name_list['lead_time'] = 3
        pyfortracc.forecast(name_list, read_function)

    forecast_files = sorted(glob.glob(name_list['output_path'] +
                                      'forecast/19000101_0015/forecasttable/*.parquet'))
    forecast_table = pd.concat(pd.read_parquet(f) for f in forecast_files)

See :doc:`BI_FORECAST` for how the forecast works, its outputs and how to verify it.


8. Post-process and export
-------------------------------------------------------

.. code-block:: python

    from pyfortracc.post_processing import compute_duration

    if __name__ == '__main__':
        # Total duration of each cluster (new columns 'duration' and 'genesis')
        compute_duration(name_list)

        # Polygons and trajectories as GeoJSON, cluster masks as NetCDF
        pyfortracc.spatial_conversions(name_list, read_function,
                                       boundary=True, trajectory=True, cluster=True)

See :doc:`BI_POSTPROCESSING` for adding external raster and vector data, rasterizing the
tracking table and exporting to the classic ForTraCC format.


Output folder
-------------------------------------------------------

After these steps the output folder looks like this:

.. code-block:: text

    output/
    ├── track/
    │   ├── trackingtable/       # tracking table (one parquet per time step)
    │   ├── geometry/
    │   │   ├── boundary/        # cluster polygons (GeoJSON)
    │   │   └── trajectory/      # trajectories (GeoJSON)
    │   └── clusters/            # cluster masks (NetCDF)
    └── forecast/
        └── 19000101_0015/       # one folder per forecast_time
            ├── forecast_images/
            ├── forecasttable/
            └── geometry/boundary/


Complete script
-------------------------------------------------------

.. code-block:: python

    import glob
    import numpy as np
    import pandas as pd
    from PIL import Image
    import pyfortracc
    from pyfortracc.post_processing import compute_duration


    def read_function(path):
        img = np.array(Image.open(path).convert('L')).astype(float)
        return np.where(img < 250, 1.0, 0.0)


    name_list = {
        'input_path': 'input/',
        'output_path': 'output/',
        'thresholds': [1],
        'min_cluster_size': [3],
        'operator': '>=',
        'timestamp_pattern': 'frame_%M.png',
        'delta_time': 1,
        'lon_min': -60.0, 'lon_max': -55.0,
        'lat_min': -5.0, 'lat_max': 0.0,
    }

    if __name__ == '__main__':
        pyfortracc.utilities.bubble_simulation(dir='input/')

        pyfortracc.track(name_list, read_function)

        name_list['forecast_time'] = '1900-01-01 00:15:00'
        name_list['observation_window'] = 3
        name_list['lead_time'] = 3
        pyfortracc.forecast(name_list, read_function)

        compute_duration(name_list)
        pyfortracc.spatial_conversions(name_list, read_function,
                                       boundary=True, trajectory=True, cluster=True)

        files = sorted(glob.glob('output/track/trackingtable/*.parquet'))
        tracking_table = pd.concat(pd.read_parquet(f) for f in files)
        print(tracking_table[['timestamp', 'uid', 'status', 'size', 'lifetime', 'duration']])
