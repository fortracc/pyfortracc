5. Track High-Resolution Global Precipitation
=======================================================

1. Track Global Precipitation Data

    The data for this example is Self-Calibrating Multivariate Precipitation Retrieval (SCaMPR) Rainfall Rate product RRQPE. 
    The SCaMPR precipitation product is available every 10 minutes, over the Earth globe. Each precipitation data (netDF file) 
    composite has 18000 x 6501 grid points, with high spatial resolution (2 km immediately below the satellite).

    .. code-block:: python

        # Download the ScamPR dataset
        !pip install --upgrade --no-cache-dir gdown &> /dev/null
        !gdown 'https://drive.google.com/uc?id=1CWei3m5xti6_JIoWzmMQj-NtGQ30YdlQ'
        !unzip -qq -o input.zip
        !rm -rf input.zip

    **Read Function:**

    The read_function is a Python definition function to read individual file and returns a 2D numpy array. Note: This function is mandatory 
    for the Algorithm package, as it is used to read data passing a path as parameter. Below is the code of how the function should be defined.

    .. code-block:: python

        import netCDF4 as nc
        import numpy as np
        def read_function(path):
            return nc.Dataset(path)['RRQPE'][:].data

    .. code-block:: python

        data = read_function('./input/RRQPE-INST-GLB_v1r1_blend_s202201010000000.nc')
        print('Shape of the data:', data.shape)
        print('Data type:', data.dtype)
        print('Min:', np.nanmin(data),'mm/h and', np.nanmax(data), 'mm/h')
        print('Example of the data:\n', data)

2. Setting the environment

    Install package to environment and import the package.

    .. code-block:: python

        # Run this cell to install the latest version of pyfortracc from the main branch
        # !pip install --upgrade git+https://github.com/fortracc-project/pyfortracc.git@main#egg=pyfortracc
        # Or import the local version of pyfortracc
        # %reload_ext autoreload
        # %autoreload 2
        # import sys
        # sys.path.append('../../')

    **Import library**

    If everything is correct after installing the package, you can import the library.

    .. code-block:: python

        import pyfortracc

3. Track Parameters: Name List

    For this example we will track precipitation clusters with thresholds of 1mm/h and a minimum cluster size of 500 pixels, which 
    corresponds to systems with an estimated size of 1000 km² (500 pixels * 2 km²/pixel). We will use the simple clustering method 
    from the scipy 'ndimage.labels' library and enable the option to find clusters that are on the side edge (edges = True).

    The namelist is a python dictionary with the parameters for the correct track processing. Some of these parameters are mandatory 
    and necessary for the complete tracking process, and others can be using to improve the performance of. If you need to consult these 
    parameters you can use fortracc.default_parameters command. Or, open the file fortracc/default_parameters.py file.

    .. code-block:: python

        name_list = {} # Set name_list dict
        name_list['input_path'] = 'input/' # path to the input data
        name_list['output_path'] = 'output/' # path to the output data
        name_list['thresholds'] = [1] # list of thresholds set as target (for this exemple each threshold are in mm/h)
        name_list['min_cluster_size'] = [500] # list of minimum size for cluster (in pixels)
        name_list['operator'] = '>=' # 'operator for segmentation process (>, >=, <, <=' or '==')
        name_list['timestamp_pattern'] = 'RRQPE-INST-GLB_v1r1_blend_s%Y%m%d%H%M%S0.nc' # timestamp file pattern format codes https://docs.python.org/3/library/datetime.html#format-codes
        name_list['delta_time'] = 10 # delta time interval (in minutes)
        name_list['cluster_method'] = 'ndimage' # Clustering method 'dbscan' (slower) or 'ndimage' (fast)
        name_list['edges'] = True # It is used to perform the cluster linking in the edges of the domain, is True if clusters cross the domain.

    .. code-block:: python

        # Run the tracking process
        pyfortracc.track(name_list, read_function, parallel=True)

4. Track Visualization

    The visualization module is a fortracc utility designed to read the algorithm outputs and display the track and its other information 
    in an easy way for the user.

    Before calling the visualization utility, it will be necessary to add some information to the name list. This information is useful for 
    carrying out geospatial data conversions. The information being:

    .. code-block:: python

        # Add spatial information for use plot utility
        name_list['x_dim'] = 18000 # number of points in x
        name_list['y_dim'] = 6501 # number of points in y
        name_list['lon_min'] = -180.0 # Min longitude of data in degrees
        name_list['lon_max'] = 179.98 # Max longitude of data in degrees
        name_list['lat_min'] = -60.0 # Min latitude of data in degrees
        name_list['lat_max'] = 70.0 # Max latitude of data in degree

    .. code-block:: python

        # view track image for a given time. The red polygons represent the objects identified according to the threshold chosen in the name_list
        pyfortracc.plot(name_list, read_function, '2022-01-01 00:50:00')

    .. code-block:: python

        # Show cross edges clusters
        pyfortracc.plot(name_list, read_function, '2022-01-01 00:50:00', cmap='turbo', info=True,info_cols=['uid'], uid_list=[463])

    .. code-block:: python

        # Plot animation utility passing a period between '2022-01-01 00:00:00' to '2022-01-01 01:00:00'
        pyfortracc.plot_animation(name_list, read_function,
                                figsize=(20,5), # Figure size
                                cmap='turbo', #Color map of plot
                                start_stamp = '2022-01-01 00:00:00', # Timestamp start for animation
                                end_stamp = '2022-01-01 01:00:00', # Timestamp end for animation
                                uid_list=[463], # Uid list to filter
                                info_cols=['uid','lifetime'],
                                info=True, # Information box
                )

    .. code-block:: python

        #The utility's views also have configurations through their parameters.
        pyfortracc.plot(name_list, read_function, '2022-01-01 00:50:00',
                        cmap='turbo', # Color map of plot
                        zoom_region=[-60,-30,0,20], # Select a region [longitude_min, longitude_max, latitude_min, latitude_max]
                        info=True, # Show a box contain information from tracking table
                        info_cols=['uid','status','lifetime'], # Select column to show in information
                        uid_list=[272, 206], # Filter by uid
                        vector=True, vector_scale=20, vector_color='w', # Add vector direction (Vector scale is the size of arrow plot)
                        )

    Another visualization utility is plot_animation, which works similar to plot. However, in this module the user must spend a period that 
    corresponds to tracked data for a tracking animation to be generated.

    .. code-block:: python

        # Plot animation utility passing a period between '2022-01-01 00:00:00' to '2022-01-01 01:00:00'
        pyfortracc.plot_animation(name_list, read_function,
                                figsize=(15,5), # Figure size
                                cmap='turbo', #Color map of plot
                                start_stamp = '2022-01-01 00:00:00', # Timestamp start for animation
                                end_stamp = '2022-01-01 01:00:00', # Timestamp end for animation
                                uid_list=[272, 206], # Uid list to filter
                                info=True, # Information box
                                zoom_region=[-60,-30,0,20], #Zoom at region
                )

    .. code-block:: python

        # Plot animation utility passing a period between '2022-01-01 00:00:00' to '2022-01-01 01:00:00' and applying a zoom region
        pyfortracc.plot_animation(name_list, read_function,
                                figsize=(15,5), # Figure size
                                cmap='turbo', #Color map of plot
                                start_stamp = '2022-01-01 00:00:00', # Timestamp start for animation
                                end_stamp = '2022-01-01 01:00:00', # Timestamp end for animation
                                uid_list=[272], # Uid list to filter
                                info=True, # Information box
                                info_cols=['uid'],
                                zoom_region=[-50,-45,10,15], #Zoom at region
                                traj_color='white' , traj_linewidth=5,
                                centroid=True, centr_color='green', centr_size=10,
                                vector=True, vector_scale=15, vector_color='w',
                )

6. Track Output (The Tracking Table)

    The tracking table is the generalized output entity of the algorithm; it is formed by the set of files (.parquet) located in the output directory of the same name ('output_path/trackingtable'). The information obtained in the tracking process is stored in a tabular format and organized according to the tracking time. Listed below are the names of the columns (output variables) and what they represent.

    - Each row in the tracking table contains specific data related to a cluster at its corresponding threshold level.
    - The information spans from unique identifiers and descriptive statistics to geometric properties and temporal features.
    - The tracking table structure provides a comprehensive view of grouped entities, facilitating analysis and understanding of patterns across different threshold levels.

    Reading track files in the parquet format is efficiently done through the Dask library. Dask is a powerful Python library for parallel computing, designed to handle large datasets and facilitate distributed operations. By using Dask to read trace files in the parquet format, we can leverage its lazy computation capability, deferring operations until strictly necessary. This, coupled with Dask's ability to scale in distributed environments, makes reading and processing large trace datasets more efficient and accessible, providing agile and scalable analysis.

    Tracking Table Columns:
    ----------------------------------------------------

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

    .. code-block:: python

        # Install dask and distributed for parallel processing
        !pip install dask distributed --upgrade &> /dev/null

    .. code-block:: python

        # Import dask dataframe to read output tracking table
        import dask.dataframe as dd
        tracking_table = dd.read_parquet('output/track/trackingtable/*.parquet').compute()

    .. code-block:: python

        tracking_table.tail(3)

7. Post Processegin - Compute Duration

    To process overall cluster duration statistics, you can use the fortracc.post_processing.compute_duration post-processing method. This method groups 
    clusters by uid and calculates the overall duration of events. With this module, a new column is created in the tracking_table called 'duration'.

    .. code-block:: python

        # Call the post-processing utility to compute the duration of the objects
        pyfortracc.post_processing.compute_duration(namelist=name_list)

    Applying some spatial conventions to the tracking table

    .. code-block:: python

        tracking_table = dd.read_parquet('output/track/trackingtable/*.parquet').compute()
        tracking_table.head()

        .. code-block:: python

        # or Mount lifetime directly from tracking table
        tracking_table = tracking_table.set_index('timestamp')
        lifetime = tracking_table.groupby('uid')['lifetime'].max().to_frame()
        lifetime = lifetime.sort_values(by='lifetime', ascending=False)
        lifetime.head(5)

    .. code-block:: python

        # Spatial degree to pixel conversion for column size
        PIXEL_SIZE = 2 # IN KM
        tracking_table['size'] = tracking_table['size'] * PIXEL_SIZE ** 2

    **Individual Clusters Exploration**

    As a demonstration to explore the tracking results, you can select the tracked clusters individually. To do this, simply select the 'uid' and 
    apply filters to the DataFrame in the same style as the Pandas library.

    In the example below we will select just one cluster to explore its tracking characteristics.

    .. code-block:: python

        # Set the cluster uid
        CLUSTER_UID = 272
        filterd_cluster = tracking_table.loc[tracking_table['uid'] == CLUSTER_UID]
        filterd_cluster.head(3)

    .. code-block:: python

        import matplotlib.pyplot as plt
        import pandas as pd
        import warnings
        warnings.filterwarnings('ignore')

    .. code-block:: python

        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        f1 = filterd_cluster['size'].plot(ax=ax, marker='o', linestyle='dashed', color='r')
        f2 = ax.quiver(filterd_cluster.index, filterd_cluster['size'], filterd_cluster['u_'], filterd_cluster['v_'], color='b', 
                    scale=0.5, scale_units='xy')
        ax.scatter(filterd_cluster.index, filterd_cluster['size'], s=1000, facecolors='none', edgecolors='black', alpha=0.5)
        ax.scatter(filterd_cluster.index, filterd_cluster['size'], marker='+', color='black', s=1000, alpha=0.5)
        # At each index create a box with the information of the cluster
        for i in range(len(filterd_cluster)):
            ax.text(filterd_cluster.index[i] + pd.Timedelta(minutes=1),
                    filterd_cluster['size'][i] + 100,
                    f'status:{filterd_cluster["status"][i]}\n'
                    f'life:{filterd_cluster["lifetime"][i].seconds//60} min\n'
                    f'max:{filterd_cluster["max"][i]:.2f}mm/h\n'
                    f'mean:{filterd_cluster["mean"][i]:.2f}mm/h\n'
                    f'std:{filterd_cluster["std"][i]:.2f}mm/h\n'
                    f'Q1:{filterd_cluster["Q1"][i]:.2f}mm/h\n'
                    f'Q2:{filterd_cluster["Q2"][i]:.2f}mm/h\n'
                    f'Q3:{filterd_cluster["Q3"][i]:.2f}mm/h\n',
                    fontsize=6, color='black', zorder=10, weight="bold",
                    bbox=dict(facecolor='white', alpha=0.3, edgecolor='black', boxstyle='round,pad=0.5'))

        # Set the title and labels
        ax.set_title('Evolution of the cluster: {}'.format(CLUSTER_UID))
        ax.set_ylim(filterd_cluster['size'].min() - 1500, filterd_cluster['size'].max() + 1500)
        ax.set_xlim(filterd_cluster.index.min() - pd.Timedelta(minutes=15),
                    filterd_cluster.index.max() + pd.Timedelta(minutes=30))
        # Add grid at each 10 minutes
        ax.grid(True, which='both', axis='both', linestyle='--')

    .. code-block:: python

        fig, ax = plt.subplots(1, 1, figsize=(10, 3))

        f1 = tracking_table.loc[tracking_table['uid'].isin(lifetime.head().index.values)][['uid','size']].groupby('uid')['size'].plot(ax=ax,
                                                                                                                                    legend=True,
                                                                                                                                    marker='o',
                                                                                                                                    linestyle='dashed');
        ax.set_ylabel('Size (Km²)')
        ax.set_xlabel('Timestamp')
        ax.set_title('Top 5 clusters with the longest lifetime')
        grid = ax.grid(True, which='both', axis='both', linestyle='--')
        # limit the x axis to the first 1000 minutes
        ax.set_xlim(tracking_table.index.min() -  pd.Timedelta(minutes=10), tracking_table.index.max() + pd.Timedelta(minutes=10))

8. Using Dask Distributed Client

    The output data being parquet files, it is possible to use distributed processing by the dask library.

    .. code-block:: python

        # Read the tracking table
        tracking_table = dd.read_parquet('output/track/trackingtable/*.parquet').compute()

    .. code-block:: python

        import pandas as pd
        import dask.dataframe as dd
        from dask.distributed import Client
        from dask.distributed import progress, wait

    .. code-block:: python

        # Set dask Client to use in the next steps
        client = Client()
        def compute_dask(dask_df):
            future = client.compute(dask_df)
            progress(future, notebook=False) # Show progress
            wait(future) # Wait for all tasks to finish
            return future.result()

    .. code-block:: python

        # Read the tracking table
        tracking_table = dd.read_parquet('output/track/trackingtable/*.parquet',
                                        columns=['uid','duration','iuid','threshold','size','mean','max'])

    .. code-block:: python

        # Filter the tracking table
        tracking_table['iuid'] = tracking_table['iuid'].fillna(tracking_table['uid'])
        tracking_table = tracking_table[tracking_table['duration'] >= pd.Timedelta('10 minutes')]

    .. code-block:: python

        # Compute main statistics for thresholds
        statistics_dsk = tracking_table.groupby(['iuid','threshold']).agg({'iuid': ['count'],
                                                                    'duration':['max'],
                                                                    'size': ['min', 'mean', 'max'],
                                                                    'mean': ['min', 'mean', 'max'],
                                                                    'max': ['min', 'mean', 'max'],
                                                                    })
        statistics_dsk.columns = ['_'.join(col).strip() for col in statistics_dsk.columns.values]
        statistics_df = compute_dask(statistics_dsk)

    .. code-block:: python

        statistics_df.groupby('threshold')['duration_max'].agg(['count','mean','std','min','max'])











