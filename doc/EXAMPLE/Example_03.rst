3. Track Infra-Red Data 
=======================================================

1. Download the data

    The GOES-16 satellite data from Channel 13, processed by INPE (National Institute for Space Research), are available for 
    download at this link: 

    https://ftp.cptec.inpe.br/goes/goes16/retangular/.

    These data represent infrared channel information and have been reprojected onto a rectangular grid over South America. 
    This reprocessing ensures that the data are more accessible and useful for various applications, including weather forecasting, 
    environmental monitoring, and climate studies.

    The script below downloads the data from the INPE server and saves it to the local directory. The data are available in NetCDF 
    format, and the script uses the `wget` command to download the files from the INPE public FTP server.

    .. code-block:: python

        import os
        import re
        import subprocess
        from concurrent.futures import ThreadPoolExecutor

        def list_files(url):
            result = subprocess.run(['wget','--no-check-certificate','-q','-O','-', url],
                capture_output=True,
                text=True)
            nc_files = re.findall(r'href="([^"]*\.nc)"', result.stdout)
            return sorted(nc_files)

        def download_file(url, folder):
            if not os.path.exists(folder):
                os.makedirs(folder)
            filename = url.split('/')[-1]
            file_path = os.path.join(folder, filename)
            subprocess.run(['wget','--no-check-certificate','-q', '-O', file_path, url])

        def download_all_nc_files(base_url, nc_files, folder='input'):
            with ThreadPoolExecutor() as executor:
                urls = [base_url + file for file in nc_files]
                executor.map(download_file, urls, [folder] * len(urls))
            print('Downloaded all files')

        # Set the year and month
        year = 2021
        month = 6

        url = 'https://ftp.cptec.inpe.br/goes/goes16/retangular/ch13/' + str(year) + '/' + str(month).zfill(2) + '/'
        nc_files = list_files(url)[0:10]
        download_all_nc_files(url, nc_files)

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

        # Import the pyfortracc module
        import pyfortracc

3. Read Function

    The `read_function` reads the data from the NetCDF file and returns a NumPy array containing the data. We select Band 1 
    of the NetCDF file, which corresponds to the infrared channel of the GOES-16 satellite, and divide the data by 100 to convert 
    it to temperature in Kelvin.

    .. code-block:: python

        # Import the netCDF4 library and define the read_function passing path as parameter
        import xarray as xr
        def read_function(path):
            ds=xr.open_dataset(path)
            # please check the name of the variable related to latitude and longitude
            # print all variable names:
            # crop the image to the region of interest, comment the line below to use the full image
            ds=ds.sel(lon=slice(-75,-41),lat=slice(-12,8))
            return ds['Band1'].data / 100

4. Parameters: name_list

    The `name_list` function creates a list of the files in the specified directory. It receives the path to the directory as input 
    and returns a list of the files contained within. We track the convective systems by a threshold of 235 K and a minimum area of 1000 km².

    .. code-block:: python

        name_list = {} # Set name_list dict
        name_list['input_path'] = 'input/'
        name_list['output_path'] = 'output/'
        name_list['thresholds'] = [235]
        name_list['min_cluster_size'] = [300]
        name_list['operator'] = '<='
        name_list['timestamp_pattern'] = 'S10635346_%Y%m%d%H%M.nc'
        name_list['delta_time'] = 10
        name_list['cluster_method'] = 'ndimage'
        name_list['min_overlap'] = 25

5. Track Infra-Red Data

    The `track` function receives the data as input and use name_list to track the convective systems.

6. Visualize the Track Output

    The `plot` function receives the data and the track as input and plots the data and the track on the same map.
    We need set the dimensions of the plot, the projection, and the extent of the plot.

    .. code-block:: python

        # For better visualization, the values greater than 235 are set to NaN
        import numpy as np
        def plot_function(path):
            ds=xr.open_dataset(path)
            # please check the name of the variable related to latitude and longitude
            # print all variable names:
            # crop the image to the region of interest, comment the line below to use the full image
            ds=ds.sel(lon=slice(-75,-41),lat=slice(-12,8))
            data = ds.copy()
            data = data['Band1'].data / 100
            # Set the values greater than 235 to NaN
            data = np.where(data > 235, np.nan, data)
            return data

        def dim_function(path):
            ds=xr.open_dataset(path)
            # please check the name of the variable related to latitude and longitude
            # print all variable names:
            # crop the image to the region of interest, comment the line below to use the full image
            ds=ds.sel(lon=slice(-75,-41),lat=slice(-12,8))
            data = ds.copy()
            data = data['Band1'].data / 100
            # Set the values greater than 235 to NaN
            data = np.where(data > 235, np.nan, data)
            #retunr the value of the dimensions, lon_min, lon_max, lat_min, lat_max:
            return [data.shape[0], data.shape[1],ds.lon.min().values,ds.lon.max().values,ds.lat.min().values,ds.lat.max().values]

        dims = dim_function('input/S10635346_202202010000.nc')
        print(dims[0], dims[1], dims[2], dims[3], dims[4], dims[5])
        # Set the name_list dict for plotting
        name_list['x_dim'] = dims[1]
        name_list['y_dim'] = dims[0]
        name_list['lon_min'] = dims[2]
        name_list['lon_max'] = dims[3]
        name_list['lat_min'] = dims[4]
        name_list['lat_max'] = dims[5]

    .. code-block:: python

        # Plot the clusters
        pyfortracc.plot(name_list, plot_function, '2022-02-01 00:00:00', cmap='turbo', cbar_title='Temperature(k)', bound_color

    .. figure:: ../../examples/03_Track-Infrared-Dataset/img/track.png
            :alt: Track iamge

    .. code-block:: python

        # Zoom in the region
        pyfortracc.plot_animation(name_list, plot_function,
                                figsize=(10,5),
                                cmap='turbo',
                                start_stamp = '2022-02-01 00:00:00',
                                end_stamp = '2022-02-01 01:30:00',
                                uid_list=[],
                                info=True,
                                info_cols=['uid','status'],
                                vector=True, vector_scale=60
                )

    Once Loop Reflect 

7. Convert the parquets files to a tracking family like fortracc file and csv

    .. code-block:: python

        from pyfortracc.post_processing import convert_parquet_to_family, convert_parquet_to_csv
        convert_parquet_to_family(name_list)
