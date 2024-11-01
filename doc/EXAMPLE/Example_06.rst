6. Track Deforestation Dataset
=======================================================

    .. code-block:: python

        # !pip install --upgrade git+https://github.com/fortracc-project/pyfortracc.git@main#egg=pyfortracc

    .. code-block:: python

        # # If you want run the library from the source code, uncomment the following lines
        import sys
        library_path = '../../'
        sys.path.append(library_path)
        %load_ext autoreload
        %autoreload 2

    .. code-block:: python

        import pyfortracc

    .. code-block:: python

        # Run the following command to install the GDAL library
        # !sudo apt install gdal-bin -y

    .. code-block:: python

        import os
        import pathlib
        import threading
        pathlib.Path('input').mkdir(parents=True, exist_ok=True)
        url = 'https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_8/lclu/coverage/brasil_coverage_{}.tif'
        box = '-55 -3.54 -54 -4.46' # lonmin latmax lonmax latmin
        def download(command):
            os.system(command)
        for year in range(1985, 2023):
            url2 = url.format(year)
            gdal_command = 'gdal_translate /vsicurl/'+url2+' -b 1 -projwin ' + box + ' -of GTiff -outsize 1024 1024 input/'+str(year)+'.tif'
            threading.Thread(target=download, args=(gdal_command,)).start()

    .. code-block:: python

        import rasterio
        import numpy as np
        def read_function(path):
            with rasterio.open(path) as src:
                data = src.read(1)[::-1]
            # Natural mask based on class
            # https://brasil.mapbiomas.org/wp-content/uploads/sites/4/2023/08/EN__Codigos_da_legenda_Colecao_7.pdf
            natural_mask = [1,3,4,5,49,10,11,12,32,29,50,13]
            antropogenic_mask = [14,15,18,19,39,20,40,62,41,36,46,47,48,9,21]
            # Apply natural mask, everything else is antropogenic
            data = np.where(np.isin(data, antropogenic_mask), 1, 0)
            return data

    .. code-block:: python

        name_list = {} # Set name_list dict
        name_list['input_path'] = 'input/'
        name_list['output_path'] = 'output/'
        name_list['thresholds'] = [1]
        name_list['min_cluster_size'] = [5]
        name_list['operator'] = '=='
        name_list['timestamp_pattern'] = '%Y.tif'
        name_list['delta_time'] = 525960 # Minutes in a year
        name_list['delta_tolerance'] = 60 * 24# Minutes in a day
        name_list['min_overlap'] = 10
        name_list['cluster_method'] = 'ndimage'
        name_list['opt_correction'] = True
        name_list['validation'] = True

    .. code-block:: python

        pyfortracc.track(name_list, read_function, parallel=True)

    .. code-block:: python

        name_list['x_dim'] = 1024
        name_list['y_dim'] = 1024
        name_list['lon_min'] = -55.0
        name_list['lon_max'] = -54.0
        name_list['lat_min'] = -4.46
        name_list['lat_max'] = -3.54

    .. code-block:: python

        pyfortracc.plot_animation(name_list, read_function, start_stamp='1985', end_stamp='2022', trajectory=False)

    .. code-block:: python

        pyfortracc.plot_animation(name_list, read_function, start_stamp='1985', end_stamp='2022', 
                                zoom_region=[-54.6, -54.5, -3.8, -3.9], 
                                x_scale=0.001, y_scale=0.001, info=True, info_cols=['uid','status'],
                                trajectory=False, vector=True,  vector_color='white', vector_scale=1)

    .. code-block:: python

        import pandas as pd
        import glob
        tracking_files = sorted(glob.glob(name_list['output_path'] + '/track/trackingtable/*.parquet'))
        tracking_table = pd.concat(pd.read_parquet(f) for f in tracking_files)
        display(tracking_table.head())

        # Apply size of pixels, each pixel is 100m x 100m
        tracking_table['area'] = tracking_table['size'] * 100

    .. code-block:: python

        lifetime = tracking_table.groupby('uid')['lifetime'].max().to_frame()
        lifetime = lifetime.sort_values(by='lifetime', ascending=False)
        lifetime.head(5)

    .. code-block:: python

        uid_list = lifetime.index[0:10].tolist()
        tracking_table.loc[tracking_table['uid'].isin(uid_list)].groupby('uid')['area'].plot(legend=True, 
                                                                                            title='Area of the 10 largest clusters',
                                                                                            xlabel='Timestamp', 
                                                                                            ylabel='Area (m²)');

