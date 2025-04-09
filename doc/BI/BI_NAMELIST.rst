Name List
========================================================

The name list is a Python dictionary containing the necessary parameters for configuring the tracking process. 
Some parameters are mandatory for complete tracking, while others are optional, allowing for customization and improved performance. 
You can view the full list of parameters by using the command ``pyfortracc.default_parameters`` or by opening the ``pyfortracc/default_parameters.py`` file.

Mandatory Parameters
--------------------------------------------------------
- **input_path**: Path to the input files.
- **output_path**: Path for saving the output tracking files.
- **thresholds**: A Python list of intensity thresholds used in the segmentation process.
- **min_cluster_size**: A list specifying the minimum cluster size (in number of points) for each threshold during clustering.
- **operator**: String representing the comparison operator used to separate groups in the segmentation process (e.g., '>=', '<=', '==').
- **timestamp_pattern**: File name pattern for reading and timestamp conversion.
- **delta_time**: Time interval for each file or the desired interval between frames in the track (in minutes).

Example of a Name List with Mandatory Parameters
--------------------------------------------------------

.. code-block:: python

    # Empty list
    name_list = {}
    # Path to the input data
    name_list['input_path'] = 'input/'               
    # Path to save output data
    name_list['output_path'] = 'output/'             
    # Thresholds in dBZ for segmentation
    name_list['thresholds'] = [20, 30, 40]           
    # Minimum points per cluster for each threshold
    name_list['min_cluster_size'] = [10, 5, 3]       
    # Comparison operator: '>=', '<=', or '=='
    name_list['operator'] = '>='                         
    # Pattern for timestamp extraction from filenames
    name_list['timestamp_pattern'] = '%Y%m%d_%H%M%S.nc'  
    # Time interval in minutes
    name_list['delta_time'] = 12                         

Optional Parameters
--------------------------------------------------------
These parameters allow you to include geospatial information in the tracking process. If they are not set, the algorithm will proceed without geospatial data.

- **lon_min**: Minimum longitude in degrees.
- **lon_max**: Maximum longitude in degrees.
- **lat_min**: Minimum latitude in degrees.
- **lat_max**: Maximum latitude in degrees.

Example with Optional Parameters
--------------------------------------------------------

.. code-block:: python

    # Minimum longitude
    name_list['lon_min'] = -62.1475 
    # Maximum longitude    
    name_list['lon_max'] = -57.8461
    # Minimum latitude   
    name_list['lat_min'] = -5.3048
    # Maximum latitude
    name_list['lat_max'] = -0.9912

Additional Parameters
--------------------------------------------------------
These parameters provide advanced configuration options for pyForTraCC, enabling users to customize the tracking process further. They are not mandatory but can be used to fine-tune the algorithm for specific use cases.

- **mean_dbz**: If `True`, the mean reflectivity is used for tracking. Default is `False`.
- **cluster_method**: Clustering method to use. Options are `'ndimage'` or `'dbscan'`. Default is `'ndimage'`.
- **eps**: Epsilon distance for clustering when using the `'dbscan'` method. Default is `1`.
- **delta_tolerance**: Maximum time difference (in minutes) allowed between two files for tracking. Default is `0`.
- **num_prev_skip**: Number of previous files to skip during tracking. Default is `0`.
- **edges**: Whether to use domain edges for cluster linking. Options are `True` or `False`. Default is `False`.
- **n_jobs**: Number of parallel jobs to run. Default is `-1` (uses all available cores).
- **min_overlap**: Minimum overlap (in pixels) between clusters to consider them the same. Default is `10`.
- **convex_hull**: If `True`, the convex hull is used to calculate cluster geometry. Default is `False`.
- **preserv_split**: If `True`, split lifetime events are preserved for NEW/SPLIT events. Default is `False`.
- **spl_correction**: Enables vector correction for split events. Default is `False`.
- **mrg_correction**: Enables vector correction for merge events. Default is `False`.
- **inc_correction**: Enables vector correction for inner cells. Default is `False`.
- **opt_correction**: Enables optical flow vector correction. Default is `False`.
- **opt_mtd**: Optical flow method to use. Options are `'farneback'` or `'lucas-kanade'`. Default is `'lucas-kanade'`.
- **elp_correction**: Enables vector correction using ellipse fitting. Default is `False`.
- **calc_dir**: If `True`, calculates the direction of cluster movement. Default is `False`. (coming soon)
- **calc_speed**: If `True`, calculates the speed of cluster movement. Default is `False`. (coming soon)
- **speed_units**: Units for speed calculation. Default is `'m/s'`. (coming soon)
- **epsg**: EPSG code for spatial projection. Default is `4326`. (coming soon)

Example with Additional Parameters
--------------------------------------------------------

In the example below, the parameters indicate that the algorithm was configured to track using the `opt_correction` method, which enables the optical-flow method and uses the `opt_mtd` Farneback to enhance the vector components. Another parameter added is `min_overlap`, which specifies that the overlap percentage was changed to 15%.

.. code-block:: python

    # Enable optical flow correction
    name_list['opt_correction'] = True
    # Use Farneback method for optical flow
    name_list['opt_mtd'] = 'farneback'
    # Set minimum overlap for cluster matching
    name_list['min_overlap'] = 15
