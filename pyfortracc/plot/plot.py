import pathlib
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.patches as patches
from matplotlib import font_manager as mfonts
import matplotlib.patheffects as patheffects
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import LinearSegmentedColormap
from shapely.wkt import loads
from shapely.affinity import affine_transform
# from shapelysmooth import chaikin_smooth
from pyfortracc.utilities.utils import get_geotransform
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter


def plot(name_list, read_function, timestamp,
            ax=None, no_anim=True,
            uid_list=[], threshold_list=[],
            figsize=(7,7), background='default',
            scalebar=False, scalebar_metric=100,
            scalebar_location=(1.5, 0.05), plot_type='imshow',
            interpolation='nearest', ticks_fontsize=10,
            scalebar_linewidth=3, scalebar_units='km', scalebar_m_per_unit=1000,
            nan_operation=np.less_equal, nan_value=0.01,
            num_colors = 20, grid_lines=True, freq='T', title_fontsize=14,
            grid_range=True, grid_deg=30, title='Track Plot', time_zone='UTC',
            cmap = 'viridis', zoom_region=[], bounds_info=False,
            pad=0.1, orientation='vertical', shrink=0.5,
            cbar_extend='both',cbar=True, cbar_title='mm/h',
            boundary=True, centroid=True, trajectory=True, vector=False,
            info=False, info_col_name=False, smooth_trajectory=False,
            bound_color='red', bound_linewidth=1, box_fontsize=10,
            centr_color='black', centr_size=1, x_scale=0.1, y_scale=0.1,
            traj_color='blue' , traj_linewidth=1, traj_alpha=0.8,
            vector_scale=1.5, vector_color='black',
            info_cols=['uid','threshold','status'],
            save=False, save_path='output/', save_name='plot.png'):
    """
    This function is designed to visualize tracking data on a map or a simple 2D plot. 
    The function reads in tracking data, filters it based on various criteria, and plots it using Matplotlib, 
    with optional customizations such as colorbars, boundaries, centroids, trajectories, and additional information annotations. 
    """
    if read_function is None:
        print('Please set a read function to open the files!')
        return None
    # Plot by track
    if 'output_path' not in name_list:
        print('Please set the output name for the files!')
        return None
    elif name_list['output_path'] is None:
        print('Please set the output name for the files!')
        return None
    track_files = name_list['output_path'] + 'track/trackingtable/'
    # Check if trackingtable is a directory with parquet files
    if pathlib.Path(track_files).is_dir() is False:
        print('Please set a valid directory for the tracking table!')
        return None
    # Check if track_file timestamo exist
    timestamp = pd.to_datetime(timestamp)
    track_file = timestamp.strftime('%Y%m%d_%H%M.parquet')
    track_file = track_files + track_file
    if pathlib.Path(track_file).is_file() is False:
        print('The file does not exist!')
        return None
    # Read the tracking table
    tck_table = pd.read_parquet(track_file)
    # Filter by uid
    if len(uid_list) > 0:
        tck_table = tck_table.loc[tck_table['uid'].isin(uid_list)]
    if len(threshold_list) > 0:
        tck_table = tck_table.loc[tck_table['threshold'].isin(threshold_list)]
    # Check if tck_table is empty
    if len(tck_table) == 0:
        print('No data for the given filters')
        return
    tck_table = gpd.GeoDataFrame(tck_table)
    tck_table['geometry'] = tck_table['geometry'].apply(loads)
    tck_table['trajectory'] = tck_table['trajectory'].apply(loads)
    tck_table = tck_table.set_geometry('geometry')
    # Read data
    data = read_function(tck_table['file'].unique()[0])
    data = np.where(nan_operation(data, nan_value), np.nan, data)
    # Set of plot
    cmap = plt.get_cmap(cmap)
    colors = [cmap(i) for i in range(cmap.N)]
    cmap = LinearSegmentedColormap.from_list('mycmap', colors, N=num_colors)
    # Mount main figure
    fig = plt.figure(figsize=figsize)
    if 'lon_min' in name_list and 'lon_max' in name_list \
            and 'lat_min' in name_list and 'lat_max' in name_list:
            geo_transform, _= get_geotransform(name_list)
            tck_table['geometry'] = tck_table['geometry'].affine_transform(geo_transform)
            tck_table['trajectory'] = tck_table['trajectory'].apply(lambda x:affine_transform(x,geo_transform))
            if ax is None:
                ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
            if background == 'stock':
                ax.stock_img()
            elif background == 'default':
                ax.add_feature(cfeature.LAND, edgecolor='black', facecolor='lightgray', alpha=0.1)
                ax.add_feature(cfeature.OCEAN)
                ax.add_feature(cfeature.COASTLINE)
                ax.add_feature(cfeature.BORDERS, linestyle=':')
                ax.add_feature(cfeature.LAKES, alpha=0.5)
                ax.add_feature(cfeature.RIVERS)
                # ax.add_feature(cfeature.STATES.with_scale('10m'))
            if no_anim:
                gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=False,
                linewidth=1, color='gray', alpha=0.5, linestyle='--')
                gl.top_labels = False
                gl.right_labels = False
            extent = [name_list['lon_min'], name_list['lon_max'],
                    name_list['lat_min'], name_list['lat_max']]
            ax.set_extent(extent, crs=ccrs.PlateCarree())
            if plot_type == 'imshow':
                ax.imshow(data, cmap=cmap, origin='lower', extent=extent,
                            interpolation=interpolation)
            elif plot_type == 'contourf':
                ax.contourf(data, cmap=cmap, origin='lower', extent=extent,
                            interpolation=interpolation)
            elif plot_type == 'contour':
                ax.contour(data, cmap=cmap, origin='lower', extent=extent,
                            interpolation=interpolation)
            elif plot_type == 'pcolormesh':
                lons = np.linspace(name_list['lon_min'], name_list['lon_max'], data.shape[1])
                lats = np.linspace(name_list['lat_min'], name_list['lat_max'], data.shape[0])
                mesh = ax.pcolormesh(lons, lats, data, transform=ccrs.PlateCarree(), cmap=cmap)
            # calc pixel size
            pixel_size = (name_list['lon_max'] - name_list['lon_min']) / data.shape[1]
            pixel_size = pixel_size * 111.32
    else:
        if ax is None:
            ax = fig.add_subplot(1, 1, 1)
        ax.imshow(data, cmap=cmap, origin='lower', interpolation=interpolation)
    if len(zoom_region) == 4:
        tck_table = tck_table.cx[zoom_region[0]:zoom_region[1],
                                zoom_region[2]:zoom_region[3]]
    if len(tck_table) == 0:
        print('No data for the given zoom')
        return
    if cbar:
        if no_anim:
            # Set cax for colorbar
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="2%", pad=pad, axes_class=plt.Axes)
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(np.nanmin(data),
                                                                    np.nanmax(data)))
            plt.colorbar(sm, ax=ax, cax=cax, label=cbar_title, orientation=orientation,
                        shrink=shrink, extend=cbar_extend)
        
    # Add title to the figure
    ax.text(0.5, 1.03, title +' ' +  str(timestamp) + ' ' +  time_zone,
            horizontalalignment='center', fontsize=title_fontsize,
            verticalalignment='bottom', transform=ax.transAxes)
    if grid_range:
        ax.set_xticks(np.arange(name_list['lon_min'], 
                            name_list['lon_max'] + 1,
                            grid_deg), crs=ccrs.PlateCarree())
        ax.set_yticks(np.arange(name_list['lat_min'], 
                        name_list['lat_max'] + 1,
                        grid_deg), crs=ccrs.PlateCarree())
        lon_formatter = LongitudeFormatter(zero_direction_label=True)
        lat_formatter = LatitudeFormatter()
        ax.xaxis.set_major_formatter(lon_formatter)
        ax.yaxis.set_major_formatter(lat_formatter)
        # Set ticks font size
        ax.tick_params(axis='both', which='major', labelsize=ticks_fontsize)
    ##### BOUNDARIES ##############
    if boundary:
      thresholds = tck_table['threshold'].unique()
      bound_df = tck_table
      if len(thresholds) > 1:
        bound_df = bound_df.loc[bound_df['threshold'] == thresholds[0]]
        # Filter only boundaries inside the zoom region
        if len(zoom_region) == 4:
            bound_df = bound_df.cx[zoom_region[0]:zoom_region[1],
                                    zoom_region[2]:zoom_region[3]]
      bound_df.boundary.plot(ax=ax, color=bound_color,
                               linewidth=bound_linewidth)
      if centroid:
        bound_df.centroid.plot(ax=ax, color=centr_color, markersize=centr_size)
      if vector:
        for i, point in enumerate(bound_df.centroid):
            u = bound_df['u_'].iloc[i]
            v = bound_df['v_'].iloc[i]
            ax.quiver(point.x, point.y, u, v, scale=vector_scale,
                    color=vector_color, scale_units='inches',
                    zorder=10)
      if info:
        buffer = [patheffects.withStroke(linewidth=2, foreground="w")]
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        # Filter only boundaries.centroid inside the zoom region
        bound_df['geometry'] = bound_df['geometry'].centroid
        if len(zoom_region) == 4:
            bound_df = bound_df.cx[zoom_region[0]:zoom_region[1],
                                    zoom_region[2]:zoom_region[3]]

        for i, point in enumerate(bound_df.centroid):
            text = bound_df[info_cols].iloc[i]
            # check if have lifetime in the info_cols and convert lifetime delta to minutes
            if 'lifetime' in info_cols:
                text['lifetime'] = str(int(text['lifetime'])) + 'min'
            if 'uid' in info_cols:
                text['uid'] = int(text['uid'])
            if 'size' in info_cols and 'pixel_size' in locals():
                try:
                    text['size'] = text['size'] * pixel_size * pixel_size
                    text['size'] = f"{int(text['size']):,}".replace(",", ".") + ' km²'
                except:
                    pass
            if 'duration' in info_cols:
                text['duration'] = str(int(text['duration'])) + 'min'
            if 'max' in info_cols:
                # Around to 2 decimal places
                text['max'] = round(text['max'], 2)
                # Convert to string and add cb_title
                text['max'] = str(text['max']) + ' ' + cbar_title
            if info_col_name:
                text = '\n'.join([f'{col}:{value}' for col, value in text.items()])
            else:
                text = '\n'.join([f'{value}' for _, value in text.items()])
            ax.text(point.x + x_scale,
                    point.y + y_scale,
                    str(text),
                    fontsize=box_fontsize,
                    horizontalalignment='left',
                    verticalalignment='baseline',
                    path_effects=buffer,
                    bbox=props,
                    zorder=10)
    ##### TRAJECTORY #############
    if trajectory:
      # Apply taubin_smooth into trajectory column
    #   if smooth_trajectory:
        #   tck_table['trajectory'] = tck_table['trajectory'].apply(lambda x: chaikin_smooth(x) if x.length > 0 else x)
      traject_df = tck_table.set_geometry('trajectory')
      traject_df.plot(ax=ax, color=traj_color , linewidth=traj_linewidth, alpha=traj_alpha)
    if save:
        plt.savefig(save_path + save_name)
    plt.close(fig)
    # Add matrix info
    if bounds_info:
        ax.annotate(str(data.shape[1]) + ' Columns', xy=(0.5, -0.1), xytext=(0.5, -0.18),
            fontsize=14, ha='center', va='bottom', xycoords='axes fraction', 
            bbox=dict(boxstyle='square', fc='0.9'),
            arrowprops=dict(arrowstyle='-[, widthB=23.0, lengthB=.5', lw=2.0))
        ax.annotate(str(data.shape[0]) + ' Rows', xy=(-0.07, 0.5), xytext=(-0.1, 0.5),
                    fontsize=14, ha='center', va='center', xycoords='axes fraction', rotation=90,
                    bbox=dict(boxstyle='square', fc='.9'),
                    arrowprops=dict(arrowstyle='-[, widthB=11.5, lengthB=.6', lw=2.0))
    if scalebar:
        scale_bar(ax, ccrs.Mercator(), scalebar_metric, location=scalebar_location,
                linewidth=scalebar_linewidth, units=scalebar_units)
    if len(tck_table) > 0 and len(zoom_region) == 4:
        ax.set_xlim(zoom_region[0], zoom_region[1])
        ax.set_ylim(zoom_region[2], zoom_region[3])
    return fig

from math import floor
def utm_from_lon(lon):
    """
    utm_from_lon - UTM zone for a longitude

    Not right for some polar regions (Norway, Svalbard, Antartica)

    :param float lon: longitude
    :return: UTM zone number
    :rtype: int
    """
    return floor( ( lon + 180 ) / 6) + 1

def scale_bar(ax, proj, length, location=(0.5, 0.05), linewidth=3,
              units='km', m_per_unit=1000, bar_height=0.02, n_offset=0.01):
    """
    ax is the axes to draw the scalebar on.
    proj is the projection the axes are in.
    location is center of the scalebar in axis coordinates (0.5, 0.05 means center horizontally and 5% from the bottom).
    length is the length of the scalebar in km.
    linewidth is the thickness of the scalebar.
    units is the name of the unit.
    m_per_unit is the number of meters in a unit.
    bar_height is the height of the scale bar relative to the plot area.
    n_offset is the offset of the 'N' arrow relative to the bar.
    """
    # Get the extent of the plotted area in geodetic coordinates (lat/lon)
    x0, x1, y0, y1 = ax.get_extent(proj.as_geodetic())
    # Turn the specified scalebar location into coordinates in lat/lon
    sbcx = x0 + (x1 - x0) * location[0]
    sbcy = y0 + (y1 - y0) * location[1]

    # Generate the x coordinate for the ends of the scalebar in lat/lon
    bar_xs = [sbcx - length / 2 / 111, sbcx + length / 2 / 111]  # 1 degree ~ 111 km at the equator

    # buffer for scalebar
    buffer = [patheffects.withStroke(linewidth=5, foreground="w")]
    # Plot the scalebar in geodetic coordinates (using PlateCarree to keep it horizontal)
    ax.plot(bar_xs, [sbcy, sbcy], transform=ccrs.PlateCarree(),
            color='k', linewidth=linewidth, path_effects=buffer)

    # buffer for text
    buffer = [patheffects.withStroke(linewidth=3, foreground="w")]

    # Adjust the text for the scalebar
    t0 = ax.text(sbcx, sbcy - bar_height * (y1 - y0), str(length) + ' ' + units,
                 transform=ccrs.PlateCarree(),
                 horizontalalignment='center', verticalalignment='top',
                 path_effects=buffer, zorder=2)

    # Adjust N arrow position to be above the scale bar
    t1 = ax.text(sbcx, sbcy + n_offset * (y1 - y0), u'\u25B2\nN',
                 transform=ccrs.PlateCarree(),
                 horizontalalignment='center', verticalalignment='bottom',
                 path_effects=buffer, zorder=2)

    # Plot the scalebar without buffer, in case covered by text buffer
    ax.plot(bar_xs, [sbcy, sbcy], transform=ccrs.PlateCarree(),
            color='k', linewidth=linewidth, zorder=3)