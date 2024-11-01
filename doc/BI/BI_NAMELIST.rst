Name List
========================================================

The name list is a Python dictionary containing the necessary parameters for configuring the tracking process. 
Some parameters are mandatory for complete tracking, while others are optional, allowing for customization and improved performance. 
You can view the full list of parameters by using the command ``fortracc.default_parameters`` or by opening the ``fortracc/default_parameters.py`` file.

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