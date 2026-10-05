"""Tests for the ellipse correction (elp_correction -> u_elp / v_elp)."""
import glob

import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
from shapely.affinity import translate
from shapely.geometry import Polygon, MultiPolygon

import pyfortracc
from pyfortracc.vector_methods.ellipse_mtd import ellipse_mtd


def make_frames(prv_geoms, cur_geoms, past_idx):
    """Build cur/prv frames exactly as spatial_operations calls ellipse_mtd:
    prv_df is the previous frame indexed by the past_idx of each current row."""
    prv_frame = gpd.GeoDataFrame({'geometry': prv_geoms},
                                 index=np.arange(len(prv_geoms)))
    cur_frame = gpd.GeoDataFrame({'geometry': cur_geoms, 'past_idx': past_idx},
                                 index=np.arange(100, 100 + len(cur_geoms)))
    return cur_frame, prv_frame.loc[cur_frame['past_idx'].values]


def centroid_uv(cur_df, prv_df):
    """Vector without correction (u_noc/v_noc): centroid displacement."""
    cur_c = np.array([g.centroid.coords[0] for g in cur_df.geometry])
    prv_c = np.array([g.centroid.coords[0] for g in prv_df.geometry])
    return cur_c[:, 0] - prv_c[:, 0], cur_c[:, 1] - prv_c[:, 1]


def l_shape(x0=0.0, y0=0.0, res=1.0):
    """Asymmetric L-shaped contour following pixel edges (like a raster
    cluster boundary), with origin (x0, y0) and pixel size res."""
    pts = [(0, 0), (6, 0), (6, 2), (2, 2), (2, 9), (0, 9)]
    ring = Polygon([(x0 + x * res, y0 + y * res) for x, y in pts])
    # Densify to a vertex per pixel edge, as in a rasterised contour
    return ring.segmentize(res)


def blob(x0=0.0, y0=0.0, res=1.0):
    """Rectangular blob of 8 x 6 pixels."""
    pts = [(0, 0), (8, 0), (8, 6), (0, 6)]
    return Polygon([(x0 + x * res, y0 + y * res) for x, y in pts]).segmentize(res)


@pytest.mark.parametrize('x0, y0, res, du, dv', [
    (0.0, 0.0, 1.0, 3.0, -2.0),                # pixel coordinates
    (-60.1475, -3.3048, 0.0178, 0.0534, 0.0356),  # degrees (radar grid)
    (175.3, 10.0, 0.04, 0.37, -0.21),          # degrees near +180
])
def test_rigid_translation_matches_true_displacement(x0, y0, res, du, dv):
    """(a) Rigid translation of an asymmetric shape: elp == true shift."""
    prv = l_shape(x0, y0, res)
    cur = translate(prv, du, dv)
    cur_df, prv_df = make_frames([prv], [cur], [0])
    u_, v_ = ellipse_mtd(cur_df, prv_df)
    assert len(u_) == len(v_) == 1
    np.testing.assert_allclose(u_[0], du, rtol=0, atol=1e-6 * res)
    np.testing.assert_allclose(v_[0], dv, rtol=0, atol=1e-6 * res)


def test_deforming_shape_differs_from_centroid():
    """(b) A bulge growing on one side moves the centroid and the fitted
    ellipse centre by different amounts, so u_elp/v_elp != u_noc/v_noc."""
    prv = blob()
    bulge = Polygon([(8, 0), (14, 0), (14, 4), (8, 4)])
    cur = translate(prv, 1.0, 1.0).union(translate(bulge, 1.0, 1.0)).segmentize(1.0)
    cur_df, prv_df = make_frames([prv], [cur], [0])
    u_elp, v_elp = ellipse_mtd(cur_df, prv_df)
    u_noc, v_noc = centroid_uv(cur_df, prv_df)
    assert np.isfinite(u_elp[0]) and np.isfinite(v_elp[0])
    assert np.hypot(u_elp[0] - u_noc[0], v_elp[0] - v_noc[0]) > 0.1


@pytest.mark.parametrize('cur_geom', [
    Polygon([(0, 0), (2, 0), (1, 2)]),          # 3 contour points
    Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),  # 4 contour points
])
def test_less_than_five_contour_points_is_nan(cur_geom):
    """(c) Fewer than 5 contour points cannot be fitted: NaN."""
    cur_df, prv_df = make_frames([blob()], [cur_geom], [0])
    u_, v_ = ellipse_mtd(cur_df, prv_df)
    assert np.isnan(u_[0]) and np.isnan(v_[0])
    # The same applies when the previous system is the small one
    cur_df, prv_df = make_frames([cur_geom], [blob()], [0])
    u_, v_ = ellipse_mtd(cur_df, prv_df)
    assert np.isnan(u_[0]) and np.isnan(v_[0])


def test_multipolygon_uses_all_parts_and_ignores_holes():
    """MultiPolygon (DBSCAN cluster): exteriors of all parts, holes ignored."""
    part1 = l_shape()
    hole = [(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)]
    part1_holed = Polygon(part1.exterior.coords, [hole])
    part2 = translate(blob(), 10.0, 0.0)
    prv = MultiPolygon([part1_holed, part2])
    prv_noholes = MultiPolygon([part1, part2])
    cur = translate(prv, 2.0, 1.5)
    cur_df, prv_df = make_frames([prv, prv_noholes], [cur, cur], [0, 1])
    u_, v_ = ellipse_mtd(cur_df, prv_df)
    np.testing.assert_allclose(u_, [2.0, 2.0], atol=1e-6)
    np.testing.assert_allclose(v_, [1.5, 1.5], atol=1e-6)
    # Using only the first part would give a different centre
    cur_df, prv_df = make_frames([part1], [cur], [0])
    u_part, _ = ellipse_mtd(cur_df, prv_df)
    assert abs(u_part[0] - 2.0) > 1.0


def test_repeated_previous_index():
    """Several current systems sharing one previous system (e.g. splits),
    so prv_df has repeated index labels."""
    prv = l_shape()
    cur_a = translate(prv, 1.0, 0.0)
    cur_b = translate(prv, 0.0, 2.0)
    cur_df, prv_df = make_frames([prv], [cur_a, cur_b], [0, 0])
    assert prv_df.index.duplicated().any()
    u_, v_ = ellipse_mtd(cur_df, prv_df)
    np.testing.assert_allclose(u_, [1.0, 0.0], atol=1e-6)
    np.testing.assert_allclose(v_, [0.0, 2.0], atol=1e-6)


def read_png(path):
    from PIL import Image
    img = np.array(Image.open(path).convert('L')).astype(float)
    return np.where(img < 250, 1.0, 0.0)


@pytest.mark.parametrize('bounds, edges', [
    ((-60.0, -55.0, -5.0, 0.0), False),
    ((-180.0, 180.0, -90.0, 90.0), True),   # global grid, +-180 edges
])
def test_bubble_simulation_tracking(tmp_path, bounds, edges):
    """(d) Full tracking of the bubble simulation with elp_correction and
    validation: runs without error, u_elp differs from u_noc in most
    systems and 'elp' can be chosen by the validation."""
    input_path = str(tmp_path / 'input') + '/'
    output_path = str(tmp_path / 'output') + '/'
    # The bubbles move less than one pixel per frame and the validation
    # rounds the vectors to whole pixels, so elp and noc often tie (noc wins
    # the tie). With seed=2 the elp vector has the lowest FAR in one system.
    pyfortracc.utilities.bubble_simulation(dir=input_path, seed=2)
    lon_min, lon_max, lat_min, lat_max = bounds
    name_list = {
        'input_path': input_path,
        'output_path': output_path,
        'thresholds': [1],
        'min_cluster_size': [3],
        'operator': '>=',
        'timestamp_pattern': 'frame_%M.png',
        'delta_time': 1,
        'lon_min': lon_min, 'lon_max': lon_max,
        'lat_min': lat_min, 'lat_max': lat_max,
        'edges': edges,
        'elp_correction': True,
        'validation': True,
        'validation_scores': True,
    }
    pyfortracc.track(name_list, read_png, parallel=False)
    files = sorted(glob.glob(output_path + 'track/trackingtable/*.parquet'))
    assert len(files) == 30
    table = pd.concat(pd.read_parquet(f) for f in files)
    linked = table[table['past_idx'].notna() & table['u_noc'].notna()]
    assert len(linked) > 0
    fitted = linked[linked['u_elp'].notna()]
    differs = (~np.isclose(fitted['u_elp'], fitted['u_noc'], rtol=0,
                           atol=1e-9 * (lon_max - lon_min)) |
               ~np.isclose(fitted['v_elp'], fitted['v_noc'], rtol=0,
                           atol=1e-9 * (lat_max - lat_min)))
    assert differs.sum() > len(linked) / 2
    assert (table['method'] == 'elp').any()
