"""Tests for the lat/lon coordinates of the NetCDF outputs (pixel centres of the tracking grid)."""
import glob
import os

import numpy as np
import pandas as pd
import pytest
import xarray as xr
from rasterio import features
from shapely.geometry import LineString, Polygon

from pyfortracc.post_processing import spatial_vectors, track2raster
from pyfortracc.spatial_conversions.clusters import clusters
from pyfortracc.utilities.utils import grid_coordinates, save_netcdf

# Tracking grid: 30 x 20 pixels of 0.1 deg, bounds = outer edges, row 0 = south (as in pyForTraCC)
LON_MIN, LAT_MIN, RES, NX, NY = -61.0, -4.0, 0.1, 30, 20
LON_MAX, LAT_MAX = LON_MIN + NX * RES, LAT_MIN + NY * RES
BOUNDS = dict(lon_min=LON_MIN, lon_max=LON_MAX, lat_min=LAT_MIN, lat_max=LAT_MAX)
LON_C = LON_MIN + (np.arange(NX) + 0.5) * RES
LAT_C = LAT_MIN + (np.arange(NY) + 0.5) * RES


def cluster_masks():
    """Clusters in the south-west and north-east corners (where linspace labels were half a pixel off)
    and in the middle of the grid."""
    masks = []
    for rows, cols in [(slice(0, 3), slice(0, 2)), (slice(17, 20), slice(26, 30)), (slice(8, 12), slice(12, 17))]:
        m = np.zeros((NY, NX), bool)
        m[rows, cols] = True
        masks.append(m)
    return masks


def polygon(mask, origin=(LON_MIN, LAT_MIN), res=RES):
    """Cluster boundary built as in features_extraction/statistics.py."""
    geoms = [Polygon(g['coordinates'][0], g['coordinates'][1:])
             for g, _ in features.shapes(mask.astype('uint8'), mask, connectivity=8,
                                         transform=(res, 0, origin[0], 0, res, origin[1]))]
    assert len(geoms) == 1
    return geoms[0]


def setup_run(tmp_path, bounds=True, extra=None):
    """Input folder (one frame, only read for the grid size), a tracking table with the clusters
    and the name_list."""
    os.makedirs(tmp_path / 'input')
    np.save(tmp_path / 'input' / 'd_20140101_0000.npy', np.zeros((NY, NX), 'f4'))
    os.makedirs(tmp_path / 'output' / 'track' / 'trackingtable')
    masks = cluster_masks()
    origin, res = ((LON_MIN, LAT_MIN), RES) if bounds else ((-0.5, -0.5), 1)
    table = pd.DataFrame({
        'timestamp': pd.Timestamp('2014-01-01 00:00'),
        'uid': np.arange(1, len(masks) + 1, dtype=float),
        'iuid': np.nan,
        'threshold_level': 0,
        'threshold': 1.0,
        'size': [int(m.sum()) for m in masks],
        'lifetime': [10.0, 20.0, 30.0],
        'u_noc': [0.1, 0.2, 0.3],
        'v_noc': [-0.1, -0.2, -0.3],
        'array_y': [np.nonzero(m)[0] for m in masks],
        'array_x': [np.nonzero(m)[1] for m in masks],
        'geometry': [polygon(m, origin, res).wkt for m in masks],
    })
    if extra:
        for col, values in extra.items():
            table[col] = values
    table.to_parquet(tmp_path / 'output' / 'track' / 'trackingtable' / '20140101_0000.parquet')
    name_list = dict(input_path=str(tmp_path / 'input') + '/', output_path=str(tmp_path / 'output') + '/',
                     timestamp_pattern='d_%Y%m%d_%H%M.npy', thresholds=[1], min_cluster_size=[1],
                     operator='>=', delta_time=30)
    name_list.update(BOUNDS if bounds else dict(lon_min=None, lon_max=None, lat_min=None, lat_max=None))
    return name_list, masks


def read_npy(path):
    return np.load(path)


def test_grid_coordinates_are_pixel_centres():
    lon, lat = grid_coordinates(dict(BOUNDS, x_dim=NX, y_dim=NY))
    np.testing.assert_allclose(lon, LON_C)
    np.testing.assert_allclose(lat, LAT_C)


def test_save_netcdf_coordinates(tmp_path):
    data = np.zeros((NY, NX), 'f4')
    data[1, 28] = 7                                          # row 1 from the south, column 28
    save_netcdf(data, dict(BOUNDS), str(tmp_path / 'f.nc'))
    ds = xr.open_dataset(tmp_path / 'f.nc')
    np.testing.assert_allclose(ds.lon, LON_C)
    np.testing.assert_allclose(ds.lat, LAT_C)
    assert float(ds['data'].sel(lat=LAT_C[1], lon=LON_C[28]).squeeze()) == 7


def test_track2raster_burns_each_cluster_on_its_pixels(tmp_path):
    name_list, masks = setup_run(tmp_path)
    track2raster(name_list, read_npy, columns=['lifetime'], parallel=False)
    ds = xr.open_dataset(glob.glob(str(tmp_path / 'output' / 'track' / 'raster' / '*.nc'))[0])
    np.testing.assert_allclose(ds.lon, LON_C, atol=1e-5)
    np.testing.assert_allclose(ds.lat, LAT_C[::-1], atol=1e-5)          # rows from north to south
    values = ds['lifetime'].isel(time=0, threshold_level=0)
    assert int(values.notnull().sum()) == sum(m.sum() for m in masks)
    for mask, value in zip(masks, [10.0, 20.0, 30.0]):
        rows, cols = np.nonzero(mask)
        picked = values.sel(lat=xr.DataArray(LAT_C[rows]), lon=xr.DataArray(LON_C[cols]), method='nearest')
        assert (picked == value).all()


def test_track2raster_without_bounds(tmp_path):
    name_list, masks = setup_run(tmp_path, bounds=False)
    track2raster(name_list, read_npy, columns=['lifetime'], parallel=False)
    ds = xr.open_dataset(glob.glob(str(tmp_path / 'output' / 'track' / 'raster' / '*.nc'))[0])
    values = ds['lifetime'].isel(time=0, threshold_level=0).values      # row = y of the cluster pixels
    for mask, value in zip(masks, [10.0, 20.0, 30.0]):
        assert (values[mask] == value).all()
    assert np.isfinite(values).sum() == sum(m.sum() for m in masks)


def test_track2raster_opt_field_points(tmp_path):
    # Optical-flow vectors starting inside pixels (row 18 from the south, col 27) and (row 2, col 1)
    starts = [(LON_C[27] + 0.03, LAT_C[18] - 0.04), (LON_C[1] - 0.04, LAT_C[2] + 0.02)]
    lines = [None, LineString([starts[0], (starts[0][0] + 0.2, starts[0][1] + 0.1)]).wkt, None]
    lines[0] = LineString([starts[1], (starts[1][0] - 0.1, starts[1][1])]).wkt
    name_list, _ = setup_run(tmp_path, extra={'opt_field': lines})
    track2raster(name_list, read_npy, columns=['opt_field'], parallel=False)
    ds = xr.open_dataset(glob.glob(str(tmp_path / 'output' / 'track' / 'raster' / '*.nc'))[0])
    u = ds['u_opt_field'].isel(time=0, threshold_level=0)
    assert int(u.notnull().sum()) == 2
    assert float(u.sel(lat=LAT_C[18], lon=LON_C[27])) == pytest.approx(0.2)
    assert float(u.sel(lat=LAT_C[2], lon=LON_C[1])) == pytest.approx(-0.1)


def test_spatial_vectors_on_cluster_pixels(tmp_path):
    name_list, masks = setup_run(tmp_path)
    spatial_vectors(name_list, read_npy, parallel=False)
    ds = xr.open_dataset(glob.glob(str(tmp_path / 'output' / 'track' / 'spatial_vectors' / '*.nc'))[0])
    np.testing.assert_allclose(ds.lon, LON_C, atol=1e-5)
    np.testing.assert_allclose(ds.lat, LAT_C, atol=1e-5)
    u = ds['u_noc'].isel(time=0, threshold_level=0)
    for mask, value in zip(masks, [0.1, 0.2, 0.3]):
        rows, cols = np.nonzero(mask)
        picked = u.sel(lat=xr.DataArray(LAT_C[rows]), lon=xr.DataArray(LON_C[cols]), method='nearest')
        assert np.allclose(picked, value)


def test_cluster_masks_coordinates(tmp_path):
    name_list, masks = setup_run(tmp_path)
    clusters(name_list, '2014-01-01 00:00', '2014-01-01 00:00', read_npy, parallel=False)
    ds = xr.open_dataset(glob.glob(str(tmp_path / 'output' / 'track' / 'clusters' / '*.nc'))[0])
    np.testing.assert_allclose(ds.lon, LON_C)
    np.testing.assert_allclose(ds.lat, LAT_C)
    ids = ds['Clusters'].isel(time=0).sel({'threshold-level': 0})
    for mask, uid in zip(masks, [1, 2, 3]):
        rows, cols = np.nonzero(mask)
        assert (ids.sel(lat=xr.DataArray(LAT_C[rows]), lon=xr.DataArray(LON_C[cols])) == uid).all()
