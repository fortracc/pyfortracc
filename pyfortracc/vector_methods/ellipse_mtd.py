import cv2
import numpy as np
from shapely.ops import unary_union
from pyfortracc.utilities.math_utils import uv_components

def ellipse_mtd(cur_df, prv_df):
    '''
    Ellipse correction (elp_correction). Each system is represented by an
    ellipse fitted to its contour, and the vector is the displacement of the
    centre of this ellipse between the previous system (past_idx) and the
    current one. The fitted centre is less sensitive than the polygon centroid
    to irregular deformations of the contour of non-rigid objects.

    The ellipse is fitted by least squares to the points of the exterior
    contour (Fitzgibbon et al., 1999), with cv2.fitEllipseDirect. For a
    MultiPolygon (DBSCAN clusters) the exteriors of all parts are used. Holes
    are ignored. The ellipse is rotated (centre, axes and orientation), see
    fit_ellipse.

    When a past_idx refers to more than one previous system, the ellipse is
    fitted to the unary_union of their geometries.

    The vector is computed with uv_components in the coordinates of the
    geometries, as in the other methods: u is zonal (x) and v is meridional
    (y), in degrees (or pixels) per time step. It is NaN when the current or
    previous system has less than 5 contour points or when the fit fails or
    is degenerate.

    Parameters
    ----------
    cur_df : DataFrame
        current frame
    prev_df : DataFrame
        previous frame, indexed by the past_idx of each row of cur_df

    Returns
    ----------
    u_ : list
        list of zonal (u) components
    v_ : list
        list of meridional (v) components
    '''
    # Fitted centre of each current system
    cur_cent = np.array([fit_ellipse(geom)[0] for geom in cur_df.geometry],
                        dtype=float).reshape(-1, 2)
    # Fitted centre of each previous system, one fit per past_idx
    # prv_df repeats a previous system once per current system linked to it
    prv_geom = prv_df.geometry
    prv_geom = prv_geom[~prv_geom.index.duplicated()]
    prv_cent = {}
    for past_idx in cur_df['past_idx']:
        key = tuple(np.atleast_1d(past_idx).tolist())
        if key not in prv_cent:
            # More than one previous system: fit to the union of them
            geoms = prv_geom.loc[list(key)]
            geom = geoms.iloc[0] if len(geoms) == 1 else unary_union(geoms.values)
            prv_cent[key] = fit_ellipse(geom)[0]
    prv_cent = np.array([prv_cent[tuple(np.atleast_1d(past_idx).tolist())]
                         for past_idx in cur_df['past_idx']],
                        dtype=float).reshape(-1, 2)
    u_, v_ = uv_components(prv_cent.T, cur_cent.T)
    return list(u_), list(v_)


def contour_points(geometry):
    '''
    Points of the exterior contour of a Polygon or of all parts of a
    MultiPolygon, without the closing point of each ring. Holes are ignored.
    '''
    if geometry is None or geometry.is_empty:
        return np.empty((0, 2))
    polygons = getattr(geometry, 'geoms', [geometry])
    rings = [np.asarray(polygon.exterior.coords)[:-1, :2]
             for polygon in polygons
             if polygon.geom_type == 'Polygon' and not polygon.is_empty]
    if len(rings) == 0:
        return np.empty((0, 2))
    return np.concatenate(rings)


def fit_ellipse(geometry):
    '''
    Fit an ellipse by least squares to the exterior contour of a geometry
    (Fitzgibbon et al., 1999, cv2.fitEllipseDirect).

    The points are centred and scaled before the fit, so geographic
    coordinates keep their precision in the float32 used by OpenCV.

    Parameters
    ----------
    geometry : Polygon or MultiPolygon

    Returns
    ----------
    center : tuple
        (x, y) of the ellipse centre, in the units of the geometry
    axes : tuple
        full lengths of the two axes of the ellipse, as given by OpenCV
    angle : float
        rotation of the ellipse in degrees, as given by OpenCV
    All values are NaN when there are less than 5 distinct contour points or
    the fit fails or is degenerate (axes not positive, or centre outside the
    bounds of the contour).
    '''
    nan_ellipse = ((np.nan, np.nan), (np.nan, np.nan), np.nan)
    points = np.unique(contour_points(geometry), axis=0)
    if len(points) < 5:
        return nan_ellipse
    origin = points.mean(axis=0)
    scale = np.ptp(points, axis=0).max()
    if not np.isfinite(scale) or scale <= 0:
        return nan_ellipse
    norm_points = ((points - origin) / scale).astype(np.float32)
    try:
        (cx, cy), (ax1, ax2), angle = cv2.fitEllipseDirect(norm_points)
    except cv2.error:
        return nan_ellipse
    params = np.array([cx, cy, ax1, ax2, angle], dtype=float)
    if not np.all(np.isfinite(params)) or min(ax1, ax2) <= 0:
        return nan_ellipse
    # The centre of an ellipse fitted to a closed contour lies inside the
    # bounds of its points; otherwise the fit is degenerate
    lower = norm_points.min(axis=0)
    upper = norm_points.max(axis=0)
    if not (lower[0] <= cx <= upper[0] and lower[1] <= cy <= upper[1]):
        return nan_ellipse
    center = (origin[0] + cx * scale, origin[1] + cy * scale)
    axes = (ax1 * scale, ax2 * scale)
    return center, axes, float(angle)
