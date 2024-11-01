1. Introducing pyFortraCC 
=======================================================

1. Load pyfortracc package

    When all dependencies will be installed in the current Python environment and the code will be ready to use.

    .. code-block:: python

        import pyfortracc
        print('pyFortracc version', pyfortracc.__version__)

2. Example Data

    The dataset used in this example consists of files in NetCDF format. This synthetic dataset was created to simulate the movement of cells in a 2D domain. 
    The values of each cell represent reflectivity, equivalent to radar reflectivity. To download the dataset, run the following command:

    .. code-block:: python

        # Download example data and unzip to input folder
        !wget -q --show-progress https://zenodo.org/api/records/10624391/files-archive -O input.zip
        !unzip -qq -o input.zip -d input
        !rm input.zip

    or directly in the terminal

    .. code-block:: console

        wget -q --show-progress https://zenodo.org/api/records/10624391/files-archive -O input.zip
        unzip -qq -o input.zip -d input
        rm input.zip

    The reading function is responsible for individually reading the input data. It must be implemented as a Python function that extracts the 
    necessary information for tracking and returns a 2-dimensional numpy array as a result.

    .. code-block:: python

        # Read_function data get a path and return a numpy array
        import xarray as xr
        def read_function(path):
            data = xr.open_dataarray(path).data
            return data

    The next cell show and example how to use read_function to read the example data, and print some information about the data.

    .. code-block:: python

        import numpy as np
        import glob

        files = sorted(glob.glob('input/*.nc'))
        sample_data = read_function(files[0])
        print('Shape of the data:', sample_data.shape)
        print('Data type:', sample_data.dtype)
        print('Min:', np.nanmin(sample_data),'dBZ and', np.nanmax(sample_data), 'dBZ')
        print('Example of the data:\n', sample_data)

    The fortracc library has a module that allows you to view the input data, to do this simply run the command line below. An animation of data 
    that represents the movement of several cells present in the synthetic data.

    .. code-block:: python

        pyfortracc.plot_animation(path_files='input/*.nc', read_function=read_function,  cbar_title='dBZ', cmap='viridis')

3. Parameters

    The namelist is a Python dictionary that contains the parameters for the correct track processing. Some of these parameters are mandatory and 
    necessary for the complete tracking process, and others can be using to improve the performance of. If you need to consult these parameters you 
    can use fortracc.defaulta_parameters command. Or, open the file fortracc/default_parameters.py file.

    Mandatory parameters:

        * input_path: (String) path to input files.
        * output_path: (String) output path indicating the destination of the trace output files.
        * thresholds: (list) Intensity thresholds to be used in the segmentation process
        * min_cluster_size: (list) Minimum size of clusters that will be used during the clustering process.
        * operator: (String) Comparison operators that will be used to separate the groups during the segmentation process.
        * timestamp_pattern: (String) File name pattern for reading and timestamp conversion.
        * delta_time: (String) Time interval of the files or the desired interval for the track.

    .. code-block:: python

        # Example Name list dictionary of mandatory parameters
        name_list = {}
        name_list['input_path'] = 'input/' # path to the input data
        name_list['output_path'] = 'output/' # path to the output data
        name_list['thresholds'] = [20,30,40] # in dbz
        name_list['min_cluster_size'] = [10,5,3] # in number of points per cluster
        name_list['operator'] = '>=' # '>= - <=' or '=='
        name_list['timestamp_pattern'] = '%Y%m%d_%H%M%S.nc' # timestamp file pattern
        name_list['delta_time'] = 12 # in minutes

    .. code-block:: python

        # Show the default parameters
        pyfortracc.default_parameters?

4. Track Routine

    The tracking module groups the main objectives of the algorithm. This module uses the tracking parameters and the data reading function, 
    and only with this information is it possible to carry out the entire tracking process of the objects present in the input data. The output 
    of this module will be the tracking files, and they will be located in the trackingtable directory, which gives the name to the same entity 
    that we will see in the next topic. Furthermore, it is worth highlighting that each step of the tracking module groups other modules (Features 
    Extraction, Spatial Operations, Cluster linking and Result Containment) intended for the object tracking process.

    .. code-block:: python

        # You could also run all the functions in one line using the track function
        # Note: The parallel option is not available in for Mac OS in Notebook, but it works in the terminal at using __name__ == '__main__'
        pyfortracc.track(name_list, read_function, parallel=False)

5. Tracking table

    The tracking table is the generalized output entity of the algorithm, it is formed by the set of files (.parquet) that are located in the 
    output directory of the same name ('output_path/trackingtable'). The information obtained in the tracking process is stored in a tabular format, 
    and is organized according to the tracking time. Listed below are the names of the columns (output variables) and what they represent.

        * Each row of tracking table is related to a cluster at its corresponding threshold level.
        * The information spans from unique identifiers and descriptive statistics to geometric properties and temporal features.
        * The Tracking table structure provides a comprehensive view of grouped entities, facilitating analysis and understanding of patterns across different threshold levels.

    Tracking table columns:

        * *timestamp* (datetime64[us]): Temporal information of cluster.
        * *uid* (float64): Unique idetifier of cluster.
        * *iuid* (float64): Internal Unique idetifier of cluster.
        * *threshold_level* (int64): Level of threshold.
        * *threshold* (float64): Specific threshold.
        * *lifetime* (timedelta64[ns]): Cluster lifespan.
        * *status* (object): Entity status (NEW, CONTINUOUS, SPLIT, MERGE, SPLIT/MERGE)
        * *u_*, *v_* (float64): Vector components.
        * *inside_clusters* (object): Number of inside clusters.
        * *size* (int64): Cluster size in pixels.
        * *min*, *mean*, *max*, *std*, *Q1*, *Q2*, *Q3* (float64): Descriptive statistics.
        * *delta_time* (timedelta64[us]): Temporal variation.
        * *file* (object): Associated file name.
        * *array_y*, *array_x* (object): Cluster array coordinates.
        * *vector_field* (object): Associated vector field.
        * *trajectory* (object): Cluster's trajectory.
        * *geometry* (object): Boundary geometric representation of the cluster.

    Read the tracking table and concatenate the information in a single dataframe. For this, we will use glob and pandas libraries.

    .. code-block:: python

        import pandas as pd
        import glob

    .. code-block:: python

        tracking_files = sorted(glob.glob(name_list['output_path'] + '/track/trackingtable/*.parquet'))
        tracking_table = pd.concat(pd.read_parquet(f) for f in tracking_files)
        display(tracking_table.head())

6. Track Visualization

    To check the tracking results visually, the algorithm has a visualization module that allows you to check the tracking results based on the data 
    in the tracking table. However, before calling the 'plot' and 'plot_animation' functions it is necessary to add geospatial information to the name_list, 
    which will be done in the cell below.

    .. code-block:: python

        # To add plot the tracking data
        name_list['x_dim'] = 241 # number of points in x
        name_list['y_dim'] = 241 # number of points in y
        name_list['lon_min'] = -62.1475 # Min longitude of data in degrees
        name_list['lon_max'] = -57.8461 # Max longitude of data in degrees
        name_list['lat_min'] = -5.3048 # Min latitude of data in degrees
        name_list['lat_max'] = -0.9912 # Max latitude of data in degrees

    .. code-block:: python

        # Visualize the tracking data
        pyfortracc.plot_animation(read_function=read_function, name_list=name_list, 
                                figsize=(14,5), cbar_title='dBZ',
                                threshold_list=[20],
                                info=True, info_col_name=True, 
                                start_stamp = '2014-02-12 10:00:00', 
                                end_stamp='2014-02-12 14:12:00')

7. Utilities

    A utility present in the library is spatial_conversions. This module converts the data present in the tracking_table to the most popular geospatial 
    data formats (netCDF, tiff, shapefiles, GeoJson). To use this module, it will be necessary to incorporate additional information in the name_list, 
    which refers to the grid size and geospatial coordinates.

    .. code-block:: python

        # Convert the tracking data to a geospatial format
        pyfortracc.spatial_conversions(name_list, boundary=True, trajectory=True, cluster=True, vel_unit='m/s', driver='GeoJSON')