4. Track Global Precipitation JAXA GSMAP
=======================================================

    .. code-block:: python

        user = 'USER'
        password = 'PASSWORD'
        source = '/standard/v8/netcdf/'
        start_date = '2024-01-01'
        end_date = '2024-01-01'

        !python download_gsmap.py $start_date $end_date $source $user $password 

    .. code-block:: python

        import netCDF4 as nc
        import numpy as np
        def read_function(path):
            data = nc.Dataset(path)
            variable = 'hourlyPrecipRate'
            data = data[variable][:].data[0]
            return data

    .. code-block:: python

        import sys
        sys.path.append('../../')
        import pyfortracc

    .. code-block:: python

        name_list = {}
        name_list['input_path'] = 'netcdf/'
        name_list['output_path'] = 'output/'
        name_list['thresholds'] = [0.1,1,5]
        name_list['min_cluster_size'] = [10,5,3]
        name_list['operator'] = '>='
        name_list['timestamp_pattern'] = ['gsmap_mvk.%Y%m%d.%H%M.v8.0000.0.nc',
                                        'gsmap_mvk.%Y%m%d.%H%M.v8.0000.1.nc']
        name_list['delta_time'] = 60
        name_list['cluster_method'] = 'ndimage'
        name_list['edges'] = True
        name_list['spl_correction'] = True
        name_list['mrg_correction'] = True
        name_list['inc_correction'] = True
        name_list['opt_correction'] = True
        name_list['validation'] = True
        name_list['validation_scores'] = True
        name_list['lon_min'] = -179.95
        name_list['lon_max'] = 179.95
        name_list['lat_min'] = -89.95
        name_list['lat_max'] = 89.95
        name_list['x_dim'] = 3600
        name_list['y_dim'] = 1800

    .. code-block:: python

        # Track the clusters
        pyfortracc.track(name_list, read_function, parallel=True)

    .. code-block:: python

        pyfortracc.spatial_conversions(name_list, boundary=True, trajectory=True, vector_field=True, cluster=True, vel_unit='m/s', driver='GeoJSON')


    .. code-block:: python

        import ftplib
        import os
        import argparse
        from datetime import datetime, timedelta
        from concurrent.futures import ThreadPoolExecutor

        # Configurações de conexão
        server = 'hokusai.eorc.jaxa.jp'
        max_workers = 5  # Número de threads para download paralelo

        def download_nc_files(ftp_details, current_dir, output_dir):
            server, user, passwd = ftp_details
            with ftplib.FTP(server) as ftp:
                ftp.login(user, passwd)
                try:
                    ftp.cwd(current_dir)
                    filenames = ftp.nlst()

                    for filename in filenames:
                        if is_nc_file(filename):
                            local_filename = os.path.join(output_dir, filename)
                            with open(local_filename, 'wb') as file:
                                ftp.retrbinary('RETR ' + filename, file.write)
                            print(f"Downloaded: {local_filename}")
                except ftplib.error_perm as e:
                    print(f"Cannot access directory: {current_dir} - {e}")

        def is_nc_file(filename):
            return filename.lower().endswith('.nc')

        def daterange(start_date, end_date):
            for n in range(int((end_date - start_date).days) + 1):
                yield start_date + timedelta(n)

        def main(start_date_str, end_date_str, base_directory, user, passwd):
            output_dir = os.path.basename(os.path.normpath(base_directory))
            os.makedirs(output_dir, exist_ok=True)

            # Parse dates from arguments
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

            ftp_details = (server, user, passwd)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for single_date in daterange(start_date, end_date):
                    year = single_date.strftime('%Y')
                    month = single_date.strftime('%m')
                    day = single_date.strftime('%d')
                    current_dir = os.path.join(base_directory, year, month, day)
                    futures.append(executor.submit(download_nc_files, ftp_details, current_dir, output_dir))

                for future in futures:
                    future.result()  # Espera a conclusão de todos os downloads

            print("Download completed.")

        if __name__ == "__main__":
            parser = argparse.ArgumentParser(description='Download GSMaP data from FTP server.')
            parser.add_argument('start_date', type=str, help='Start date in YYYY-MM-DD format')
            parser.add_argument('end_date', type=str, help='End date in YYYY-MM-DD format')
            parser.add_argument('base_directory', type=str, help='Base directory on FTP server (e.g., /realtime_ver/v8/netcdf/)')
            parser.add_argument('user', type=str, help='FTP username')
            parser.add_argument('passwd', type=str, help='FTP password')
            args = parser.parse_args()
            main(args.start_date, args.end_date, args.base_directory, args.user, args.passwd)

    .. code-block:: python

        import netCDF4 as nc
        import numpy as np

        def read_function(path):
            data = nc.Dataset(path)
            variable = 'hourlyPrecipRate'
            data = data[variable][:].data[0]
            return data

        import sys
        sys.path.append('../')
        import pyfortracc
        name_list = {}
        name_list['input_path'] = 'netcdf/'
        name_list['output_path'] = 'output/'
        name_list['thresholds'] = [0.1,1,5]
        name_list['min_cluster_size'] = [10,5,3]
        name_list['operator'] = '>='
        name_list['timestamp_pattern'] = ['gsmap_mvk.%Y%m%d.%H%M.v8.0000.0.nc',
                                        'gsmap_mvk.%Y%m%d.%H%M.v8.0000.1.nc']
        name_list['delta_time'] = 60
        name_list['cluster_method'] = 'ndimage'
        name_list['edges'] = True
        name_list['spl_correction'] = True
        name_list['mrg_correction'] = True
        name_list['inc_correction'] = True
        name_list['opt_correction'] = True
        name_list['validation'] = True
        name_list['validation_scores'] = True
        name_list['lon_min'] = -179.95
        name_list['lon_max'] = 179.95
        name_list['lat_min'] = -89.95
        name_list['lat_max'] = 89.95
        name_list['x_dim'] = 3600
        name_list['y_dim'] = 1800

        # Track the clusters
        # pyfortracc.track(name_list, read_function, parallel=True)
        # pyfortracc.post_processing.add_geofeature(name_list,
        #                                           'masks/region/region.shp', 
        #                                           'region', 
        #                                           'region')
        import numpy as np
        from rasterio.transform import from_origin
        from rasterio.io import MemoryFile
        def read_raster(path):
            data = np.load(path)
            data = data['data']
            # Swap the data because the jaxa data begins from 0E to 360E
            data = np.concatenate((data[:,data.shape[1]//2:], data[:,:data.shape[1]//2]), axis=1)
            min_lat = -90.0000
            max_lat = 90.0000
            min_lon = -180
            max_lon = 180
            # Calculate spatial resolution
            res_lat = (max_lat - min_lat) / data.shape[0]
            res_lon = (max_lon - min_lon) / data.shape[1]
            rows = int((max_lat - min_lat) / res_lat)
            cols = int((max_lon - min_lon) / res_lon)
            transform = from_origin(min_lon, max_lat, res_lon, res_lat)
            with MemoryFile() as memfile:
                with memfile.open(driver='GTiff', width=cols, 
                                height=rows, count=1, 
                                dtype=data.dtype,
                                crs='+proj=latlong',
                                transform=transform) as dataset:
                    dataset.write(data, 1)
                memfile.seek(0)
                raster_in_memory = memfile.open()
            return raster_in_memory 

        pyfortracc.post_processing.add_rasterfeature(name_list, 
                                                    'raster/v_component_of_wind/850/', 
                                                    'v_850',
                                                    '%Y%m%d_%H%M%S.npz',
                                                    read_raster,
                                                    parallel=True)
        # pyfortracc.spatial_conversions(name_list, boundary=True, trajectory=False, cluster=False, vel_unit='m/s', driver='GeoJSON')