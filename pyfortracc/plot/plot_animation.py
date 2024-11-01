import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from matplotlib import animation
from matplotlib.colorbar import Colorbar
from mpl_toolkits.axes_grid1 import make_axes_locatable
from IPython.display import HTML
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO
from PIL import Image
from .plot import plot
from pyfortracc.default_parameters import default_parameters

def process_frame(args):
    """Wrapper function to enable multiprocessing of the update function."""
    frame, read_function, cmap, cbar_min, cbar_max = args
    fig, ax = plt.subplots(figsize=(5, 5))
    data = read_function(frame)
    ax.imshow(data, cmap=cmap, origin='lower', interpolation='nearest', aspect='auto',
              vmin=cbar_min, vmax=cbar_max)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.grid(linestyle='-', linewidth=0.5, alpha=0.5)
    ax.set_title(f'{frame}')

    # Convert figure to image and close to free memory
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return Image.open(buf)

def plot_wrapper(args):
      return plot(*args)

def plot_animation(
        path_files=None,
        num_frames=10,
        name_list=None,
        read_function=None,
        start_timestamp='2020-01-01 00:00:00',
        end_timestamp='2020-01-01 00:00:00',
        ax=None,
        animate=True,
        uid_list=[],
        threshold_list=[],
        figsize=(7,7),
        background='default',
        scalebar=False,
        scalebar_metric=100,
        scalebar_location=(1.5, 0.05),
        plot_type='imshow',
        interpolation='nearest',
        ticks_fontsize=10,
        scalebar_linewidth=3,
        scalebar_units='km',
        min_val=None,
        max_val=None,
        nan_operation=np.less_equal,
        nan_value=0.01,
        num_colors = 20,
        title_fontsize=14,
        grid_deg=None,
        title='Track Plot',
        time_zone='UTC',
        cmap = 'viridis',
        zoom_region=[],
        bounds_info=False,
        pad=0.2,
        orientation='vertical',
        shrink=0.5,
        cbar_extend='both',
        cbar=True,
        cbar_title='',
        boundary=True,
        centroid=True, trajectory=True, vector=False,
        info=True,
        info_col_name=True,
        smooth_trajectory=True,
        bound_color='red', 
        bound_linewidth=2, 
        box_fontsize=10,
        centr_color='black',
        centr_size=2,
        x_scale=0.1,
        y_scale=0.1,
        traj_color='black',
        traj_linewidth=2,
        traj_alpha=1,
        vector_scale=0.5,
        vector_color='black',
        info_cols=['uid'],
        save=False,
        save_path='output/',
        save_name='plot.png'):
    
      if name_list is not None:
            name_list = default_parameters(name_list, read_function)
      print('Generating animation...', end=' ', flush=True)

      # Get the list of frames
      if path_files is not None:
            files = sorted(glob.glob(path_files, recursive=True))[:num_frames]
            # Process each frame in parallel and store images in a list
            with ProcessPoolExecutor() as executor:
                  frames = list(executor.map(process_frame, [(frame, read_function, cmap, min_val, max_val) for frame in files]))
      else:
            files = sorted(glob.glob(name_list['output_path'] + 'track/trackingtable/*.parquet'))
            files = pd.to_datetime([f.split('/')[-1] for f in files], format='%Y%m%d_%H%M.parquet')
            files = files[(files >= start_timestamp) & (files <= end_timestamp)]
            # Process each frame in parallel and store images in a list
            args = []
            for timestamp in files:
                  args.append((
                  name_list,
                  read_function,
                  timestamp,
                  ax,
                  animate,
                  uid_list,
                  threshold_list,
                  figsize,
                  background,
                  scalebar,
                  scalebar_metric,
                  scalebar_location,
                  plot_type,
                  interpolation,
                  ticks_fontsize,
                  scalebar_linewidth,
                  scalebar_units,
                  min_val,
                  max_val,
                  nan_operation,
                  nan_value,
                  num_colors,
                  title_fontsize,
                  grid_deg,
                  title,
                  time_zone,
                  cmap,
                  zoom_region,
                  bounds_info,
                  pad,
                  orientation,
                  shrink,
                  cbar_extend,
                  cbar,
                  cbar_title,
                  boundary,
                  centroid, trajectory,vector,
                  info,
                  info_col_name,
                  smooth_trajectory,
                  bound_color,
                  bound_linewidth,
                  box_fontsize,
                  centr_color,
                  centr_size,
                  x_scale,
                  y_scale,
                  traj_color,
                  traj_linewidth,
                  traj_alpha,
                  vector_scale,
                  vector_color,
                  info_cols,
                  save,
                  save_path,
                  save_name))

            with ProcessPoolExecutor() as executor:
                  frames = list(executor.map(plot_wrapper, args))

      # Set up the figure for the animation
      fig, ax = plt.subplots(figsize=figsize)
      img = ax.imshow(np.zeros((10, 10)), cmap=cmap)  # Dummy initial image
      ax.axis('off')
      
      interval = 1000  # Interval between frames in milliseconds
      repeat_delay = 5000  # Delay before repeating the animation

      def update(i):
            img.set_data(frames[i])
            return [img]

      ani = animation.FuncAnimation(fig, update, frames=len(frames), interval=interval, repeat=True, blit=False, repeat_delay=repeat_delay)
      
      ani_html = ani.to_jshtml()
      plt.close(fig)
      return HTML(ani_html)



