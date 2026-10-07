"""Tests for add_raster_data / add_vector_data (post-processing of the tracking table)."""
import glob
import os

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest
import rioxarray  # noqa: F401  (.rio accessor)
import xarray as xr
from rasterio import features
from shapely.geometry import Polygon, box

from pyfortracc.post_processing import add_raster_data, add_vector_data

# Tracking grid: 30 x 20 pixels of 0.1 deg, row 0 = south (as in pyForTraCC)
LON_MIN, LAT_MIN, RES, NX, NY = -61.0, -4.0, 0.1, 30, 20
LON_MAX, LAT_MAX = LON_MIN + NX * RES, LAT_MIN + NY * RES


def cluster_masks():
    """Three clusters: an L shape, a square ring with a hole and a single pixel."""
    masks = []
    m = np.zeros((NY, NX), bool)
    m[2:9, 3:5] = True
    m[2:4, 5:10] = True
    masks.append(m)
    m = np.zeros((NY, NX), bool)
    m[10:16, 15:21] = True
    m[12:14, 17:19] = False
    masks.append(m)
    m = np.zeros((NY, NX), bool)
    m[18, 28] = True
    masks.append(m)
    return masks


def polygon(mask):
    """Cluster boundary built as in features_extraction/statistics.py."""
    geoms = [Polygon(g['coordinates'][0], g['coordinates'][1:])
             for g, _ in features.shapes(mask.astype('uint8'), mask, connectivity=8,
                                         transform=(RES, 0, LON_MIN, 0, RES, LAT_MIN))]
    assert len(geoms) == 1
    return geoms[0]


def write_table(output_path, times, empty=()):
    """Tracking table with the three clusters in every frame (YYYYMMDD_HHMM.parquet)."""
    folder = os.path.join(output_path, 'track', 'trackingtable')
    os.makedirs(folder)
    masks = cluster_masks()
    for t in times:
        t = pd.Timestamp(t)
        rows = [] if t in [pd.Timestamp(e) for e in empty] else masks
        pd.DataFrame({
            'timestamp': pd.Series([t] * len(rows), dtype='datetime64[ns]'),
            'uid': np.arange(len(rows), dtype=float),
            'size': np.array([m.sum() for m in rows], dtype='int64'),
            'geometry': pd.Series([polygon(m).wkt for m in rows], dtype=object),
        }).to_parquet(os.path.join(folder, f'{t:%Y%m%d_%H%M}.parquet'))
    return masks


def pixel_ids(factor=1):
    """Raster whose value is the id (row * NX + col, row 0 = south) of the tracking pixel that contains each
    raster pixel, at `factor` raster pixels per tracking pixel. Returns (array north-up, lat, lon)."""
    nx, ny, res = NX * factor, NY * factor, RES / factor
    lon = LON_MIN + (np.arange(nx) + 0.5) * res
    lat = LAT_MAX - (np.arange(ny) + 0.5) * res
    col = np.floor((lon - LON_MIN) / RES).astype(int)
    row = np.floor((lat - LAT_MIN) / RES).astype(int)
    return (row[:, None] * NX + col[None, :]).astype('float64'), lat, lon


def to_dataarray(values, lat, lon, lat_ascending=False, lon_descending=False):
    da = xr.DataArray(values, coords={'lat': lat, 'lon': lon}, dims=('lat', 'lon'), name='v')
    if lat_ascending:
        da = da.isel(lat=slice(None, None, -1))
    if lon_descending:
        da = da.isel(lon=slice(None, None, -1))
    return da                                  # the CRS is set by read_raster


def read_raster(path):
    return xr.open_dataarray(path).rio.write_crs('EPSG:4326')


def read_table(output_path):
    files = sorted(glob.glob(os.path.join(output_path, 'track', 'trackingtable', '*.parquet')))
    return pd.concat([pd.read_parquet(f).assign(file=os.path.basename(f)) for f in files])


@pytest.mark.parametrize('lat_ascending, lon_descending', [(False, False), (True, False), (False, True)])
def test_each_cluster_gets_exactly_its_pixels(tmp_path, lat_ascending, lon_descending):
    out = str(tmp_path) + '/'
    masks = write_table(out, ['2014-01-01 00:00'])
    values, lat, lon = pixel_ids()
    raster = tmp_path / 'raster.nc'
    to_dataarray(values, lat, lon, lat_ascending, lon_descending).to_netcdf(raster)
    add_raster_data({'output_path': out}, raster_function=read_raster, raster_path=str(raster),
                    merge_mode='fixed', statistics=['values', 'count'], parallel=False)
    table = read_table(out)
    for mask, (_, row) in zip(masks, table.iterrows()):
        rows, cols = np.nonzero(mask)
        assert sorted(row['v_values']) == sorted((rows * NX + cols).astype(float).tolist())
        assert row['v_count'] == row['size'] == mask.sum()


@pytest.mark.parametrize('factor', [2, 3])
def test_finer_raster_counts_every_subpixel(tmp_path, factor):
    out = str(tmp_path) + '/'
    masks = write_table(out, ['2014-01-01 00:00'])
    values, lat, lon = pixel_ids(factor)
    raster = tmp_path / 'raster.nc'
    to_dataarray(values, lat, lon).to_netcdf(raster)
    add_raster_data({'output_path': out}, raster_function=read_raster, raster_path=str(raster),
                    merge_mode='fixed', statistics=['count', 'mean'], parallel=False)
    table = read_table(out)
    for mask, (_, row) in zip(masks, table.iterrows()):
        rows, cols = np.nonzero(mask)
        assert row['v_count'] == factor ** 2 * mask.sum()
        assert row['v_mean'] == pytest.approx((rows * NX + cols).mean())


def test_frames_at_half_past_get_their_own_raster(tmp_path):
    out = str(tmp_path) + '/'
    times = pd.date_range('2014-01-01 00:00', periods=4, freq='30min')
    write_table(out, times)
    _, lat, lon = pixel_ids()
    for k, t in enumerate(times):
        to_dataarray(np.full((NY, NX), float(k)), lat, lon).to_netcdf(tmp_path / f'r_{t:%Y%m%d_%H%M}.nc')
    add_raster_data({'output_path': out}, raster_function=read_raster, raster_path=str(tmp_path / 'r_*.nc'),
                    raster_file_pattern='r_%Y%m%d_%H%M.nc', statistics='mean', parallel=False)
    table = read_table(out)
    expected = table['timestamp'].map({t: float(k) for k, t in enumerate(times)})
    assert (table['v_mean'] == expected).all()


def test_tolerance_mode_without_raster_gives_no_data(tmp_path):
    out = str(tmp_path) + '/'
    times = pd.date_range('2014-01-01 00:00', periods=3, freq='30min')
    write_table(out, times)
    _, lat, lon = pixel_ids()
    for k in (0, 2):  # no raster for 00:30
        to_dataarray(np.full((NY, NX), float(k)), lat, lon).to_netcdf(tmp_path / f'r_{times[k]:%Y%m%d_%H%M}.nc')
    add_raster_data({'output_path': out}, raster_function=read_raster, raster_path=str(tmp_path / 'r_*.nc'),
                    raster_file_pattern='r_%Y%m%d_%H%M.nc', merge_mode='tolerance', time_tolerance='10min',
                    statistics=['mean', 'count'], parallel=False)
    table = read_table(out).set_index('timestamp')
    assert (table.loc[times[0], 'v_mean'] == 0).all() and (table.loc[times[2], 'v_mean'] == 2).all()
    assert table.loc[times[1], 'v_mean'].isna().all() and (table.loc[times[1], 'v_count'] == 0).all()


def test_frame_without_clusters_and_written_schema(tmp_path):
    out = str(tmp_path) + '/'
    times = pd.date_range('2014-01-01 00:00', periods=3, freq='30min')
    write_table(out, times, empty=[times[1]])
    values, lat, lon = pixel_ids()
    raster = tmp_path / 'raster.nc'
    to_dataarray(values, lat, lon).to_netcdf(raster)
    folder = os.path.join(out, 'track', 'trackingtable')
    before = {f: pd.read_parquet(f) for f in sorted(glob.glob(folder + '/*.parquet'))}
    add_raster_data({'output_path': out}, raster_function=read_raster, raster_path=str(raster),
                    merge_mode='fixed', statistics=['mean', 'max', 'count', 'percentile_90'], parallel=False)
    schemas = set()
    for f, original in before.items():
        new = pd.read_parquet(f)
        pd.testing.assert_frame_equal(new[original.columns], original)   # original columns untouched
        schema = pq.read_schema(f)
        assert b'geo' not in (schema.metadata or {})                       # plain parquet, WKT geometry
        schemas.add(tuple((n, str(schema.field(n).type)) for n in schema.names if n not in original))
    assert len(schemas) == 1                                               # same new columns and types in every file
    assert len(pd.read_parquet(os.path.join(folder, f'{times[1]:%Y%m%d_%H%M}.parquet'))) == 0


def test_cluster_outside_the_raster(tmp_path):
    out = str(tmp_path) + '/'
    write_table(out, ['2014-01-01 00:00'])
    values, lat, lon = pixel_ids()
    raster = tmp_path / 'raster.nc'
    to_dataarray(values[:, :12], lat, lon[:12]).to_netcdf(raster)       # only the western 12 columns
    add_raster_data({'output_path': out}, raster_function=read_raster, raster_path=str(raster),
                    merge_mode='fixed', statistics=['mean', 'count'], parallel=False)
    table = read_table(out)
    assert table['v_count'].tolist() == [cluster_masks()[0].sum(), 0, 0]
    assert table['v_mean'].isna().tolist() == [False, True, True]
    assert table['v_mean'].dtype == 'float64' and table['v_count'].dtype == 'int64'


def test_values_with_positions_on_the_tracking_grid(tmp_path):
    out = str(tmp_path) + '/'
    masks = write_table(out, ['2014-01-01 00:00'])
    values, lat, lon = pixel_ids(2)                                        # finer raster, resampled to the grid
    raster = tmp_path / 'raster.nc'
    to_dataarray(values, lat, lon).to_netcdf(raster)
    name_list = {'output_path': out, 'lon_min': LON_MIN, 'lon_max': LON_MAX, 'lat_min': LAT_MIN,
                 'lat_max': LAT_MAX, 'x_dim': NX, 'y_dim': NY}
    add_raster_data(name_list, raster_function=read_raster, raster_path=str(raster), merge_mode='fixed',
                    statistics='values', return_positions=True, parallel=False)
    table = read_table(out)
    for mask, (_, row) in zip(masks, table.iterrows()):
        rows, cols = np.nonzero(mask)
        assert sorted(row['v_values']) == sorted((rows * NX + cols).astype(float).tolist())
        # _xy = [col, row] with row 0 = north (track2raster convention); value = id of that pixel
        for (x, y), v in zip(row['v_xy'], row['v_values']):
            assert v == (NY - 1 - y) * NX + x
        for (lon_c, lat_c), (x, y) in zip(row['v_coords'], row['v_xy']):
            assert lon_c == pytest.approx(LON_MIN + (x + 0.5) * RES)
            assert lat_c == pytest.approx(LAT_MAX - (y + 0.5) * RES)


def test_add_vector_data_nearest_mode(tmp_path):
    out = str(tmp_path) + '/'
    times = pd.date_range('2014-01-01 00:00', periods=2, freq='30min')
    write_table(out, times)
    for k, t in enumerate(times):
        gpd.GeoDataFrame({'region': [f'region_{k}']}, geometry=[box(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX)],
                         crs='EPSG:4326').to_file(tmp_path / f'v_{t:%Y%m%d_%H%M}.geojson', driver='GeoJSON')
    add_vector_data({'output_path': out}, vector_path=str(tmp_path),
                    vector_file_pattern='v_%Y%m%d_%H%M.geojson', vector_column='region',
                    merge_mode='nearest', parallel=False)
    table = read_table(out)
    assert (table['region'] == table['timestamp'].map({t: f'region_{k}' for k, t in enumerate(times)})).all()
