2. Algorithm Workflow
=======================================================

1. Radar Data

    The data used in this example is a small sample of scans from the S-Band Radar located in Manaus, AM, Brazil. 
    The full dataset was processed and published by Schumacher, Courtney, and Funk, Aaron (2018). It is available on 
    the ARM platform at https://www.arm.gov/research/campaigns/amf2014goamazon.

    This dataset is part of the GoAmazon2014/5 project and is titled "Three-dimensional Gridded S-band Reflectivity and 
    Radial Velocity from the SIPAM Manaus S-band Radar dataset". You can access the dataset via https://doi.org/10.5439/1459573.

    .. code-block:: python

        # Download the input files
        !pip install --upgrade --no-cache-dir gdown &> /dev/null
        !gdown 'https://drive.google.com/uc?id=1UVVsLCNnsmk7_wOzVrv4H7WHW0sz8spg'
        !unzip -qq -o input.zip
        !rm -rf input.zip

2. Setting the environment

    Install package to environment and import the package.

    .. code-block:: python

        # Run this cell to install the latest version of pyfortracc from the main branch
        # !pip install --upgrade git+https://github.com/fortracc-project/pyfortracc.git@main#egg=pyfortracc
        # Or import the local version of pyfortracc
        %reload_ext autoreload
        %autoreload 2
        import sys
        sys.path.append('../../')

    .. code-block:: python

        # Import the pyfortracc package
        import pyfortracc
    
3. Read Function

    The downloaded data is compressed with the .gz extension but is of netCDF4 format. The variable representing reflectivity is DBZc. 
    The data includes multiple elevation levels, and for this example, we arbitrarily selected elevation 5, which corresponds to a 
    volumetric scan at a height of 2.5 km. After extracting the data, we apply a NaN value to mask the data where the value is -9999.

    .. code-block:: python

        # Define the Read function
        import gzip
        import netCDF4
        import numpy as np

        def read_function(path):
            variable = "DBZc"
            z_level = 5 # Elevation level 2.5 km
            with gzip.open(path) as gz:
                with netCDF4.Dataset("dummy", mode="r", memory=gz.read()) as nc:
                    data = nc.variables[variable][:].data[0,z_level, :, :][::-1, :]
                    data[data == -9999] = np.nan
            gz.close()
            return data

    .. code-block:: python

        # Visualize the data
        pyfortracc.plot_animation(path_files='input/*.gz', 
                                num_frames=10, figsize=(4, 4), cbar_min=-10, cbar_max=60,
                                read_function=read_function,  cbar_title='dBZ', cmap='viridis')

4. Tracking Parameters

    In this example, we will track reflectivity clusters using multiple thresholds and sizes. We have arbitrarily selected thresholds 
    of 20, 30, and 35 dBZ, with minimum cluster sizes of 5, 4, and 3 pixels, respectively. The segmentation operator will be >=, meaning 
    the clusters will be segmented based on values greater than or equal to each threshold. The time interval between observations is 12 
    minutes. The clustering algorithm used in this example is DBSCAN, and the overlap rate between clusters at consecutive time steps will 
    be set to 20%.

    .. code-block:: python

        # Example Name list dictionary of mandatory parameters
        name_list = {}
        name_list['input_path'] = 'input/' # path to the input data
        name_list['output_path'] = 'output/' # path to the output data
        name_list['timestamp_pattern'] = 'sbmn_cappi_%Y%m%d_%H%M.nc.gz' # timestamp file pattern
        name_list['thresholds'] = [20,30,35] # in dbz
        name_list['min_cluster_size'] = [3,3,3] # in number of points per cluster
        name_list['operator'] = '>=' # '>= - <=' or '=='
        name_list['delta_time'] = 12 # in minutes
        name_list['cluster_method'] = 'dbscan' # DBSCAN Clustering method
        name_list['min_overlap'] = 20 # Minimum overlap between clusters in percentage

5. Algorithm Workflow

    In this example, we will use the modules separately, meaning each internal module of the pyForTraCC algorithm will be called individually. 
    The tracking workflow is divided into four modules:

    * **Feature Detection**: Focuses on identifying distinct characteristics for precise tracking.
    * **Spatial Operations**: Involves spatial operations (intersection, union, difference, etc.) between the features of consecutive time steps (t and t-1).
    * **Trajectory Linking**: Processes time steps one by one, linking features from consecutive time steps based on the associations created in the previous step. The algorithm creates a trajectory for each feature.
    * **Concatenate**: Combines and processes all features across the different time steps.

    Image processing strategies are combined with clustering and rasterization algorithms to achieve the results obtained by the `extract_features` 
    function. The following sequence outlines the implementation of the algorithm:

        1. Read the file using the `read_function`.
        2. Segment the image according to each threshold.
        3. Label the clusters. Two clustering options are implemented: DBSCAN and `ndimage`.
        4. Vectorize the clusters using `rasterio.features.shapes` to acquire the boundary polygon and centroid of the clusters.
    
    .. figure:: ../../examples/02_Algorithm_Workflow_Radar_Example/img/features.png
        :alt: Alternate text for the image

    .. code-block:: python

        # (Note: If you are running this notebook using MacOS, you may need to set parallel=False)
        pyfortracc.features_extraction(name_list, read_function, parallel=True)

    The output

    .. code-block:: python

        import pandas as pd
        import glob

        dir_name = name_list['output_path'] + '/track/processing/features/*.parquet'
        features = sorted(glob.glob(dir_name))
        features = pd.concat(pd.read_parquet(f) for f in features)
        display(features.head())

    **Spatial operations**

    Spatial junctions, fundamental in Geographic Information Systems (GIS) and spatial databases. And the Geopandas implementation 
    simplifies the process by combining GeoDataframes stored in .parquet files based on their spatial relationships via the sjoin() 
    method. This method performs various types of spatial joins such as overlays, within, contains.

    To demonstrate the basic functioning of the spatial operations mode, we will use as a base two consecutive times listed here as 
    the variables cur_frame and prev_frame, which store information about the characteristics of the systems for each time.

    .. code-block:: python

        import pandas as pd
        import geopandas as gpd
        import matplotlib.pyplot as plt
        from shapely.wkt import loads

    .. code-block:: python

        # Read the features parquet files
        cur_frame = pd.read_parquet('./output/track/processing/features/20140816_1012.parquet')
        prev_frame = pd.read_parquet('./output/track/processing/features/20140816_1000.parquet')
        cur_frame['geometry'] = cur_frame['geometry'].apply(loads)
        prev_frame['geometry'] = prev_frame['geometry'].apply(loads)
        # Convert to geo dataframes where column is geometry
        cur_frame = gpd.GeoDataFrame(cur_frame)
        prev_frame = gpd.GeoDataFrame(prev_frame)

    .. code-block:: python

        # Visualize the features and see have a visual overlap between the geometries
        fig, ax = plt.subplots(1, 1, figsize=(5, 5))
        prev_frame.boundary.plot(ax=ax, color='blue', alpha=0.5)
        cur_frame.plot(ax=ax, color='red', alpha=0.5)

    .. code-block:: python

        # Display the first 5 rows of the current frame
        display(cur_frame.head())

    .. code-block:: python

        # Display the first 5 rows of the previous frame
        display(prev_frame.head())

    To demonstrate one of the operations performed in the algorithm, below is the GeoPandas sjoin function that checks the overlaps between 
    the two GeoDataframes. Note that the return of the function will be another GeoDataframe, however only the index and index_right columns 
    are of interest to us, as in these columns we have the information we need to make the associations between the geometries of the consecutive 
    time clusters. In addition to the overlap operation, there are several others that can be seen at: 
    https://shapely.readthedocs.io/en/latest/manual.html#binary-predicates

    .. code-block:: python

        # Perform the spatial join between the previous and current frame
        overlaps = gpd.sjoin(cur_frame, prev_frame, how='inner', predicate='overlaps')[['index_right']].reset_index()
        # Ex: index (cur_frame) 0 overlaps with index_right 0 (prev_franme)
        overlaps

    In addition, the spatial operations module also has additional vector extraction methods. These methods are covered in the work https://doi.org/10.3390/rs14215408

    To activate the methods just add the flags to the name_list.

    .. code-block:: python

        # Add correction methods
        name_list['spl_correction'] = True # It is used to perform the correction at Splitting events
        name_list['mrg_correction'] = True # It is used to perform the correction at Merging events
        name_list['inc_correction'] = True # It is used to perform the correction using Inner Core vectors
        name_list['opt_correction'] = True # It is used to perform the correction using the Optical Flow method
        name_list['validation'] = True # It is used to perform the validation of the correction methods

    .. code-block:: python

        # Run the spatial_operations function (Note: If you are running this notebook using MacOS, you may need to set parallel=False)
        pyfortracc.spatial_operations(name_list, read_function, parallel=True)

    .. code-block:: python

        # Read the spatial parquet files
        spatial = sorted(glob.glob(name_list['output_path'] + '/track/processing/features/*.parquet'))
        spatial_df = pd.concat(pd.read_parquet(f) for f in spatial)
        display(spatial_df.head())

    **Cluster Link**

    The cluster connection module makes the association between consecutive time tables by associating the cluster indices that were 
    identified by the spatial operations module.

    .. code-block:: python

        # Run the cluster_linking function
        pyfortracc.cluster_linking(name_list)

    Bellow we show how cluster link works. Set two spatial parquets from consecutive timestamps. And show the association between them based on indexes.

    .. code-block:: python

        # Read current and previous frames
        cur_frame = pd.read_parquet('output/track/processing/spatial/20140816_1212.parquet')
        prv_frame = pd.read_parquet('output/track/processing/spatial/20140816_1200.parquet')

    .. code-block:: python

        # Current Frame
        cur_frame.dropna(subset=['prev_idx']).head()

    .. code-block:: python

        # Previous frame
        prv_frame.loc[cur_frame['prev_idx'].dropna().astype(int).values].head()

    .. code-block:: python

        # Show the linking results
        linked = sorted(glob.glob(name_list['output_path'] + '/track/processing/linked/*.parquet'))
        linking_df = pd.concat(pd.read_parquet(f) for f in linked)
        linking_df.loc[linking_df['trajectory'] != 'LINESTRING EMPTY'].tail()

    **Concatenate**

    All features in one single file per timestamp, and create the Tracking Table.

    .. code-block:: python

        # Concatenate the features and spatial dataframes
        pyfortracc.concat(name_list, clean=True)

    The tracking table is the generalized output entity of the algorithm, formed by the set of files (.parquet) located in the output directory 
    of the same name ('output_path/trackingtable'). The information obtained during the tracking process is stored in a tabular format, organized 
    according to the tracking time. Listed below are the names of the columns (output variables) and their representations:

        - Each row in the tracking table contains specific data related to a cluster at its corresponding threshold level.
        - The information spans from unique identifiers and descriptive statistics to geometric properties and temporal features.
        - The Tracking Table structure provides a comprehensive view of grouped entities, facilitating analysis and understanding of patterns across different threshold levels.

    Tracking table columns:

        - **timestamp** (datetime64[us]): Temporal information of the cluster.
        - **uid** (float64): Unique identifier of the cluster.
        - **iuid** (float64): Internal unique identifier of the cluster.
        - **threshold_level** (int64): Level of threshold.
        - **threshold** (float64): Specific threshold.
        - **lifetime** (timedelta64[ns]): Cluster lifespan.
        - **status** (object): Entity status (NEW, CONTINUOUS, SPLIT, MERGE, SPLIT/MERGE).
        - **u_, v_** (float64): Vector components.
        - **inside_clusters** (object): Number of inside clusters.
        - **size** (int64): Cluster size in pixels.
        - **min, mean, max, std, Q1, Q2, Q3** (float64): Descriptive statistics.
        - **delta_time** (timedelta64[us]): Temporal variation.
        - **file** (object): Associated file name.
        - **array_y, array_x** (object): Cluster array coordinates.
        - **vector_field** (object): Associated vector field.
        - **trajectory** (object): Cluster's trajectory.
        - **geometry** (object): Boundary geometric representation of the cluster.

    Sorted and concatenate

    .. code-block:: python

        tracking_files = sorted(glob.glob(name_list['output_path'] + '/track/trackingtable/*.parquet'))
        tracking_table = pd.concat(pd.read_parquet(f) for f in tracking_files)
        display(tracking_table.head())

    .. code-block:: python

        # If need to save the family table into separate files or unique file run the cell below

        import pandas as pd
        import glob
        import pathlib

        tracking_files = sorted(glob.glob(name_list['output_path'] + '/track/trackingtable/*.parquet'))
        tracking_table = pd.concat(pd.read_parquet(f) for f in tracking_files)

        family_group = tracking_table.groupby('uid')
        family_table = pd.DataFrame()
        pathlib.Path('output/track/trackingtable/family').mkdir(parents=True, exist_ok=True)
        for _, group in family_group:
            family_table = pd.concat([family_table, group])
            # # If need save in separate files uncomment the line below
            # uid_ = group['uid'].iloc[0]
            # group.to_csv(f'output/track/trackingtable/family/{uid_}.csv')
        # If need save into unique file uncomment the line below
        family_table.to_csv('output/track/trackingtable/family.csv')

    Explore the results in tracking table

    .. code-block:: python

        # Get two maxlifetime clusters from the track_table
        maxlifetime = 2
        max_lifetimes = tracking_table.groupby('uid').size().nlargest(maxlifetime).index.values
        max_clusters = tracking_table[tracking_table['uid'].isin(max_lifetimes)]
        max_clusters.loc[max_clusters['threshold_level'] == 0].head()

    Visualize the track as animation

    .. code-block:: python

        # To add plot the tracking data
        name_list['lon_min'] = -62.1475 # Min longitude of data in degrees
        name_list['lon_max'] = -57.8461 # Max longitude of data in degrees
        name_list['lat_min'] = -5.3048 # Min latitude of data in degrees
        name_list['lat_max'] = -0.9912 # Max latitude of data in degrees
        name_list['x_dim'] = 241 # Number of points in the x axis
        name_list['y_dim'] = 241 # Number of points in the y axis

    .. code-block:: python

        # Plot the tracking data for periods of time
        pyfortracc.plot_animation(read_function=read_function, name_list=name_list, 
                                figsize=(14,5), cbar_title='dBZ', vector=True, vector_scale=10,
                                threshold_list=[20], uid_list=max_lifetimes.tolist(),
                                info=True, info_col_name=True, info_cols=['uid', 'method', 'far'],
                                smooth_trajectory=True,
                                start_stamp = '2014-08-16 12:24:00', 
                                end_stamp='2014-08-16 20:48:00')

    Convert the results to spatial data type.

    .. code-block:: python

        pyfortracc.spatial_conversions(name_list, boundary=True, trajectory=True, vector_field=True, cluster=True, vel_unit='m/s', driver='GeoJSON')

