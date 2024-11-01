import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from matplotlib import animation
from matplotlib.colorbar import Colorbar
from mpl_toolkits.axes_grid1 import make_axes_locatable
from IPython.display import HTML
from .plot import plot
from pyfortracc.default_parameters import default_parameters


def plot_animation(name_list = None,
                  read_function=None,
                  start_stamp = '1900-01-01 00:00:00',
                  end_stamp = '2099-01-01 00:00:00',
                  uid_list=[], threshold_list=[],
                  figsize=(5,5),
                  nan_operation=np.less_equal, 
                  min_val=None, max_val=None,
                  nan_value=0.01,
                  num_colors = 20, freq='T',
                  cmap = 'viridis', zoom_region=[],
                  pad=0.1, orientation='vertical', shrink=0.5,
                  cbar_extend='both', cbar_title='mm/h',
                  cbar_min=None, cbar_max=None, x_scale=0.1, y_scale=0.1,
                  boundary=True, centroid=True, trajectory=True, vector=False,
                  info=False, info_col_name=True, smooth_trajectory=False,
                  bound_color='red', bound_linewidth=1,
                  centr_color='black', centr_size=1,
                  traj_color='black' , traj_linewidth=2, traj_alpha=1,
                  vector_scale=0.5, vector_color='black',
                  info_cols=['uid','threshold','status'],
                  interval=500,
                  repeat_delay=1000,
                  path_files=None,
                  num_frames=None):
      """
      Generate an animated plot from geospatial or raster data.

      Parameters
      ----------
      name_list : dict, optional
            Dictionary containing metadata and parameters for the data to be plotted.
      read_function : function
            Function to read and process data for each frame of the animation.
      start_stamp : str, optional
            Start timestamp for the data to be plotted (default is '1900-01-01 00:00:00').
      end_stamp : str, optional
            End timestamp for the data to be plotted (default is '2099-01-01 00:00:00').
      uid_list : list, optional
            List of unique IDs for filtering data (default is an empty list).
      threshold_list : list, optional
            List of thresholds for filtering data (default is an empty list).
      figsize : tuple, optional
            Figure size for the plot (default is (7,7)).
      nan_operation : function, optional
            Operation to handle NaN values in the data (default is np.less_equal).
      nan_value : float, optional
            Value to consider as NaN (default is 0.01).
      num_colors : int, optional
            Number of colors to use in the colormap (default is 20).
      freq : str, optional
            Frequency for generating timestamps (default is 'T' for minute).
      cmap : str, optional
            Colormap for the plot (default is 'viridis').
      zoom_region : list, optional
            Region to zoom into for the plot [lon_min, lon_max, lat_min, lat_max] (default is an empty list).
      pad : float, optional
            Padding for the colorbar (default is 0.1).
      orientation : str, optional
            Orientation of the colorbar ('vertical' or 'horizontal', default is 'vertical').
      shrink : float, optional
            Shrink factor for the colorbar (default is 0.5).
      extend : str, optional
            Extend style for the colorbar ('both', 'min', 'max', 'neither', default is 'both').
      cbar_title : str, optional
            Title for the colorbar (default is 'mm/h').
      cbar_min : float, optional
            Minimum value for the colorbar (default is None).
      cbar_max : float, optional
            Maximum value for the colorbar (default is None).
      x_scale : float, optional
            Scale for the x-axis (default is 0.1).
      y_scale : float, optional
            Scale for the y-axis (default is 0.1).
      boundary : bool, optional
            Whether to plot boundaries (default is True).
      centroid : bool, optional
            Whether to plot centroids (default is True).
      trajectory : bool, optional
            Whether to plot trajectories (default is True).
      vector : bool, optional
            Whether to plot vectors (default is False).
      info : bool, optional
            Whether to display additional info on the plot (default is False).
      info_col_name : bool or str, optional
            Column name for additional info (default is False).
      smooth_trajectory : bool, optional
            Whether to smooth trajectories (default is False).
      bound_color : str, optional
            Color for boundaries (default is 'red').
      bound_linewidth : float, optional
            Line width for boundaries (default is 1).
      centr_color : str, optional
            Color for centroids (default is 'black').
      centr_size : float, optional
            Size of centroid markers (default is 1).
      traj_color : str, optional
            Color for trajectories (default is 'blue').
      traj_linewidth : float, optional
            Line width for trajectories (default is 1).
      traj_alpha : float, optional
            Transparency for trajectories (default is 0.8).
      vector_scale : float, optional
            Scale for vectors (default is 1.5).
      vector_color : str, optional
            Color for vectors (default is 'black').
      info_cols : list, optional
            List of columns for additional info (default is ['uid', 'status', 'lifetime']).
      interval : int, optional
            Interval between frames in milliseconds (default is 500).
      repeat_delay : int, optional
            Delay before repeating the animation in milliseconds (default is 1000).
      path_files : str, optional
            Path pattern to files to be used for the animation (default is None).
      num_frames : int, optional
            Number of frames to include in the animation (default is None).

      Returns
      -------
      html_output : IPython.display.HTML
            The HTML representation of the animation for embedding in Jupyter Notebooks.

      Description
      -----------
      The function generates an animated plot, visualizing either raster data or geospatial
      information over time. It supports customization of colormaps, colorbars, zoom regions,
      and overlays like boundaries, centroids, and trajectories. The animation can be 
      customized further by setting parameters like time intervals, number of colors, and 
      vector overlays.
      """
      if name_list is not None:
            name_list = default_parameters(name_list)
      fig = plt.figure(figsize=figsize)
      # Plot data from path_files
      if path_files is not None:
            files = sorted(glob.glob(path_files, recursive=True))
            files = files[:num_frames]
            ax = fig.add_subplot(1, 1, 1)
            def update(frame):
                  ax.clear()
                  data = read_function(frame)
                  img = ax.imshow(data, cmap=cmap, origin='lower', 
                              interpolation='nearest', aspect='auto',
                              vmin=cbar_min, vmax=cbar_max)
                  ax.set_xlabel('X')
                  ax.set_ylabel('Y')
                  ax.grid( linestyle='-', linewidth=0.5, alpha=0.5)      
                  ax.set_title(f'{frame}')
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="2%", pad=pad, axes_class=plt.Axes)
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=cbar_min, vmax=cbar_max))
            sm._A = []
            cbar = plt.colorbar(sm, cax=cax, orientation=orientation, extend=cbar_extend)
            cbar.set_label(cbar_title)
      else:
            # Mount timestamplist based on start and end time and name_list['delta_time']
            files = sorted(glob.glob(name_list['output_path'] + 'track/trackingtable/*.parquet'))
            files = [f.split('/')[-1] for f in files]
            files = pd.to_datetime(files, format='%Y%m%d_%H%M.parquet')
            files = files[(files >= start_stamp) & (files <= end_stamp)]
            if 'lon_min' in name_list and 'lon_max' in name_list and 'lat_min' in name_list and 'lat_max' in name_list:
                  if name_list['lon_min'] is not None and name_list['lon_max'] is not None and name_list['lat_min'] is not None and name_list['lat_max'] is not None:
                        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
            else:
                  ax = fig.add_subplot(1, 1, 1)
            def update(frame):
                  ax.clear()
                  ax.set_aspect('auto')
                  fplt = plot(name_list, read_function, frame, ax=ax, nan_operation=nan_operation, nan_value=nan_value, uid_list=uid_list, threshold_list=threshold_list,
                        num_colors=num_colors, cmap=cmap, zoom_region=zoom_region, pad=pad, orientation=orientation, shrink=shrink, x_scale=x_scale, y_scale=y_scale,
                        cbar_extend=cbar_extend, cbar_title=cbar_title, boundary=boundary, centroid=centroid, trajectory=trajectory, vector=vector,
                        info=info, info_col_name=info_col_name, smooth_trajectory=smooth_trajectory, bound_color=bound_color, bound_linewidth=bound_linewidth,
                        centr_color=centr_color, centr_size=centr_size, traj_color=traj_color, traj_linewidth=traj_linewidth, traj_alpha=traj_alpha,
                        vector_scale=vector_scale, vector_color=vector_color, info_cols=info_cols, no_anim=False, min_val=min_val, max_val=max_val)
                  return ax
      # Animation
      ani = animation.FuncAnimation(fig, update,
                              frames=files,
                              interval=interval, repeat=True, blit=False, 
                              repeat_delay=repeat_delay)
      ani = ani.to_jshtml()
      html_output = HTML(ani)
      plt.close(fig)
      return html_output
