
import gdown, zipfile, os, shutil
import sys
import os

import pandas as pd
import glob
import zipfile
sys.path.append('../')
import pyfortracc
# Set the read function
import gzip
import netCDF4
import numpy as np
import pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import subprocess

def read_function(path):
    variable = "DBZc"
    z_level = 5 # Elevation level 2.5 km
    with gzip.open(path) as gz:
        with netCDF4.Dataset("dummy", mode="r", memory=gz.read()) as nc:
            data = nc.variables[variable][:].data[0,z_level, :, :]
            data[data == -9999] = np.nan
    gz.close()
    return data

def download_mapbiomas(url_template: str, bbox: str, start_year: int, end_year: int, max_workers: int = 4):
    # Cria o diretório de saída se não existir
    pathlib.Path('mapbiomas').mkdir(parents=True, exist_ok=True)
    # Função interna para baixar e processar um único ano
    def _download(year: int):
        url = url_template.format(year)
        out_file = f"mapbiomas/{year}.tif"
        gdal_command = [
            "gdal_translate",
            f"/vsicurl/{url}",
            out_file,
            "-b", "1",
            "-projwin", *bbox.split(),
            "-of", "GTiff",
            "-outsize", "1024", "1024",
        ]
        subprocess.run(gdal_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return year
    # Lista de anos a serem processados
    years = list(range(start_year, end_year + 1))
    # Uso de ThreadPoolExecutor para downloads paralelos
    with tqdm(total=len(years), desc="Downloading & Processing") as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_download, y): y for y in years}
            for future in as_completed(futures):
                try:
                    _ = future.result()
                except Exception as e:
                    print(f"Erro no ano {futures[future]}: {e}")
                pbar.update(1)


# Set the parameters
name_list = {}
name_list['input_path'] = 'input/' # path to the input data
name_list['output_path'] = 'output/' # path to the output data
name_list['timestamp_pattern'] = 'sbmn_cappi_%Y%m%d_%H%M.nc.gz' # timestamp file pattern
name_list['thresholds'] = [20,30,35] # in dbz
name_list['min_cluster_size'] = [3,3,3] # in number of points per cluster
name_list['operator'] = '>=' # '>= *   **<=' or '=='
name_list['delta_time'] = 12 # in minutes
name_list['min_overlap'] = 20 # Minimum overlap between clusters in percentage

# Clustering method
name_list['cluster_method'] = 'dbscan' # DBSCAN Clustering method
name_list['eps'] = 3 # in pixels

# Vector correction methods
name_list['spl_correction'] = True # Perform the Splitting events
name_list['mrg_correction'] = True # Perform the Merging events
name_list['inc_correction'] = True # Perform the Inner Core vectors
name_list['opt_correction'] = True # Perform the Optical Flow method (New Method)
name_list['elp_correction'] = True # Perform the Ellipse method (New Method)
name_list['validation'] = True # Perform the validation of the best correction between times (t-1 and t)
name_list['validation_scores'] = True

# Optional parameters, if not set, the algorithm will not use geospatial information
name_list['lon_min'] = -62.1475 # Min longitude of data in degrees
name_list['lon_max'] = -57.8461 # Max longitude of data in degrees
name_list['lat_min'] = -5.3048 # Min latitude of data in degrees
name_list['lat_max'] = -0.9912 # Max latitude of data in degrees

name_list['mrg_expansion'] = True # Perform the expansion correction for the merging events
name_list['prv_uid'] = True #save previous uids from merge and split

if __name__ == '__main__':
    # Remove the existing input files
    shutil.rmtree('input', ignore_errors=True)

    # Download the input files
    url = 'https://drive.google.com/uc?id=1UVVsLCNnsmk7_wOzVrv4H7WHW0sz8spg'
    gdown.download(url, 'input.zip', quiet=False)
    with zipfile.ZipFile('input.zip', 'r') as zip_ref:
        for member in zip_ref.namelist():
            zip_ref.extract(member)
    os.remove('input.zip')

    url = "https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_8/lclu/coverage/brasil_coverage_{}.tif"
    bbox = "-62.1475 -0.9912 -57.8461 -5.3048"  # xmin, ymin, xmax, ymax
    download_mapbiomas(url, bbox, 2014, 2014, max_workers=1)


    pyfortracc.features_extraction(name_list, read_function, parallel=True)
    pyfortracc.spatial_operations(name_list, read_function, parallel=True)
    pyfortracc.cluster_linking(name_list)
    pyfortracc.concat(name_list, clean=False, parallel=True)
    pyfortracc.post_processing.compute_duration(name_list, parallel=True)
    pyfortracc.spatial_conversions(name_list, read_function=read_function, 
                                   boundary=True, trajectory=True, vector_field=True,
                                   cluster=True, vel_unit='m/s', driver='GeoJSON')

    # Compute spatial vectors
    pyfortracc.post_processing.spatial_vectors(name_list, read_function, parallel=True)

    ## Add raster data
    def raster_function(raster_path):
        import rioxarray
        raster = rioxarray.open_rasterio(raster_path, masked=True).squeeze()
        raster = raster.rename({'x': 'lon', 'y': 'lat'})
        return raster
    pyfortracc.post_processing.add_raster_data(name_list, raster_function=raster_function, raster_path='mapbiomas/*.tif', raster_file_pattern='%Y.tif', column_name='land_use', parallel=False, merge_mode='nearest', time_tolerance=None)

    pyfortracc.plot(name_list=name_list, timestamp='2014-08-16 10:36:00',
                    read_function=read_function, cmap='viridis', num_colors=10, figsize=(10,10),
                    boundary=True, centroid=True, trajectory=True, threshold_list=[20,35,40],
                    vector=True, info=True, info_col_name=True, smooth_trajectory=True,
                    bound_color='red', bound_linewidth=1, centr_color='black', centr_size=1,
                    x_scale=0.1, y_scale=0.1, traj_color='blue', traj_linewidth=1, traj_alpha=0.8,
                    vector_scale=20, vector_color='black', info_cols=['uid','status', 'lifetime'],
                    save=True, save_path='output/', save_name='plot.png')
    tracking_files = sorted(glob.glob(name_list['output_path'] + '/track/trackingtable/*.parquet'))
    tracking_table = pd.concat(pd.read_parquet(f) for f in tracking_files)
    tracking_table.to_csv(name_list['output_path'] + '/track/tracking_table.csv')

