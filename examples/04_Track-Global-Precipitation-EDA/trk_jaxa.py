import netCDF4 as nc
import numpy as np

def read_function(path):
    data = nc.Dataset(path)
    variable = 'hourlyPrecipRate'
    data = data[variable][:].data[0]
    return data

import sys
sys.path.append('../../')
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
name_list['elp_correction'] = True
name_list['validation'] = True
name_list['validation_scores'] = True
name_list['lon_min'] = -180
name_list['lon_max'] = 180
name_list['lat_min'] = -90
name_list['lat_max'] = 90
name_list['x_dim'] = 3600
name_list['y_dim'] = 1800
name_list['n_jobs'] = 12

# pyfortracc.features_extraction(name_list, read_function, parallel=True)
# pyfortracc.spatial_operations(name_list, read_function, parallel=True)
pyfortracc.cluster_linking(name_list)
# pyfortracc.concat(name_list, clean=True)
# pyfortracc.post_processing.compute_duration(name_list, parallel=True)


# pyfortracc.post_processing.add_geofeature(name_list,
#                                           'masks/region/region.shp', 
#                                           'region', 
#                                           'region')
# import numpy as np
# from rasterio.transform import from_origin
# from rasterio.io import MemoryFile
# def read_raster(path):
#     data = np.load(path)
#     data = data['data']
#     # Swap the data because the jaxa data begins from 0E to 360E
#     data = np.concatenate((data[:,data.shape[1]//2:], data[:,:data.shape[1]//2]), axis=1)
#     min_lat = -90.0000
#     max_lat = 90.0000
#     min_lon = -180
#     max_lon = 180
#     # Calculate spatial resolution
#     res_lat = (max_lat - min_lat) / data.shape[0]
#     res_lon = (max_lon - min_lon) / data.shape[1]
#     rows = int((max_lat - min_lat) / res_lat)
#     cols = int((max_lon - min_lon) / res_lon)
#     transform = from_origin(min_lon, max_lat, res_lon, res_lat)
#     with MemoryFile() as memfile:
#         with memfile.open(driver='GTiff', width=cols, 
#                           height=rows, count=1, 
#                           dtype=data.dtype,
#                           crs='+proj=latlong',
#                           transform=transform) as dataset:
#             dataset.write(data, 1)
#         memfile.seek(0)
#         raster_in_memory = memfile.open()
#     return raster_in_memory 

# pyfortracc.post_processing.add_rasterfeature(name_list, 
#                                              'raster/v_component_of_wind/850/', 
#                                              'v_850',
#                                              '%Y%m%d_%H%M%S.npz',
#                                              read_raster,
#                                              parallel=True)
# pyfortracc.spatial_conversions(name_list, boundary=True, trajectory=False, cluster=False, vel_unit='m/s', driver='GeoJSON')
