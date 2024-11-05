from shapely.geometry import Point
from shapely.affinity import scale
from pyfortracc.utilities.math_utils import uv_components

def ellipse_mtd(cur_df, prv_df):
    ''' 
    This method receive only events of Ellipse and create a new vector for ellipse fitting.
    The vector as created between the centroid of previous ellipse, and the centroid of current new ellipse.
    
    Parameters
    ----------
    cur_df : DataFrame
        current frame
    prev_df : DataFrame
        previous frame
        
    Returns
    ----------
    u_ : list 
        list of zonal (u) components
    v_ : list
        list of meridional (v) components
    '''  
    
    u_, v_ = [], []
    cur_df['elipse'] = cur_df.geometry.apply(envole_ellipse)
    prv_df['elipse'] = prv_df.geometry.apply(envole_ellipse)
    for _, row in cur_df.iterrows():
        cur_ellip_cent = row.elipse.centroid
        prv_ellip_cent = prv_df.loc[row['past_idx']].elipse.centroid
        # If prv_ellip_cent is more than one, get centroid between points
        if isinstance(prv_ellip_cent, Point) == False:
            prv_ellip_cent = prv_ellip_cent.unary_union.centroid
        uv_ = uv_components(prv_ellip_cent.coords[0], cur_ellip_cent.coords[0])
        u_.append(uv_[0])
        v_.append(uv_[1])
    # import matplotlib.pyplot as plt
    # fig, ax = plt.subplots()
    # cur_df.geometry.boundary.plot(ax=ax, color='red')
    # prv_df.geometry.boundary.plot(ax=ax, color='blue')
    # cur_df.elipse.boundary.plot(ax=ax, color='green')
    # prv_df.elipse.boundary.plot(ax=ax, color='green')
    # plt.show()
    # exit()
    return u_, v_


def envole_ellipse(geometry, scale_factor=1):
    centroide = geometry.centroid
    minx, miny, maxx, maxy = geometry.bounds
    semi_eixo_x = (maxx - minx) / 2
    semi_eixo_y = (maxy - miny) / 2
    elipse = Point(centroide).buffer(1)
    elipse = scale(elipse, xfact=semi_eixo_x * scale_factor, yfact=semi_eixo_y * scale_factor)
    return elipse