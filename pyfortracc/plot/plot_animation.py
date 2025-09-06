import glob
import numpy as np
import pathlib
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import animation
from mpl_toolkits.axes_grid1 import make_axes_locatable
from IPython.display import HTML
from multiprocessing import Pool
from io import BytesIO
from PIL import Image
from .plot import plot
from pyfortracc.default_parameters import default_parameters
from pyfortracc.utilities.utils import set_nworkers, check_operational_system
from matplotlib import rcParams
import warnings
warnings.filterwarnings("ignore")


def process_frame(args):
      """Wrapper function to enable multiprocessing of the update function."""
      frame, read_function, cmap, cbar_min, cbar_max, origin = args
      fig, ax = plt.subplots(figsize=(5, 5))
      data = read_function(frame)
      fi = ax.imshow(data, cmap=cmap, interpolation='nearest', aspect='auto', origin=origin,
                  vmin=cbar_min, vmax=cbar_max)
      
      # Add simple colorbar
      divider = make_axes_locatable(ax)
      cax = divider.append_axes("right", size="5%", pad=0.07)
      cbar = plt.colorbar(fi, cax=cax)
      cbar.set_label('Value')
      ax.set_xlabel('X')
      ax.set_ylabel('Y')
      ax.grid(linestyle='-', linewidth=0.5, alpha=0.5)
      ax.set_title(f'{frame}')

      # Convert figure to image and close to free memory
      buf = BytesIO()
      plt.savefig(buf, format='png', bbox_inches='tight')
      buf.seek(0)
      plt.close(fig)
      return Image.open(buf)

def plot_wrapper(args):
      return plot(*args)

def plot_animation(
        path_files=None,
        num_frames=50,
        name_list=None,
        read_function=None,
        start_timestamp='2020-01-01 00:00:00',
        end_timestamp='2020-01-01 00:00:00',
        ax=None,
        animate=True,
        uid_list=[],
        threshold_list=[],
        figsize=(6,4),
        background='default',
        scalebar=False,
        scalebar_metric=100,
        scalebar_location=(1.5, 0.05),
        plot_type='imshow',
        origin='lower',
        interpolation='nearest',
        ticks_fontsize=10,
        scalebar_linewidth=3,
        scalebar_units='km',
        min_val=None,
        max_val=None,
        nan_operation=None,
        nan_value=0.01,
        num_colors = 20,
        title_fontsize=12,
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
        bound_linewidth=1, 
        box_fontsize=10,
        centr_color='black',
        centr_size=2,
        x_scale=0.15,
        y_scale=0.15,
        traj_color='black',
        traj_linewidth=2,
        traj_alpha=1,
        vector_scale=0.5,
        vector_color='black',
        info_cols=['uid'],
        save=False,
        save_path='output/',
        save_name='plot.png',
        parallel=True):
      # Set the limit of the animation size
      rcParams['animation.embed_limit'] = 2**128
      # Set default parameters
      if name_list is not None:
            name_list = default_parameters(name_list, read_function)
      else:
            name_list = {}
      # Check if the operational system is Windows
      name_list, parallel = check_operational_system(name_list, parallel)
      print('Generating animation...', end=' ', flush=True)
      # Get the list of frames
      if path_files is not None:
            files = sorted(glob.glob(path_files, recursive=True))[:num_frames]
            if len(files) == 0:
                  raise ValueError('No files found. Check the path_files parameter.')
            if parallel:
                  with Pool() as pool:
                        frames = list(pool.imap(process_frame,
                                                          [(frame, read_function,
                                                            cmap, min_val, max_val, origin
                                                            ) for frame in files]))
                  pool.close()
            else:
                  frames = []
                  for frame in files:
                        frames.append(process_frame((frame, read_function, cmap, min_val, max_val)))
      else:
            files = sorted(glob.glob(name_list['output_path'] + 'track/trackingtable/*.parquet'))
            files = pd.to_datetime([pathlib.Path(f).name for f in files], format='%Y%m%d_%H%M.parquet')
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
                  save_name,
                  origin))
            if parallel:
                  n_workers = set_nworkers(name_list)
                  with Pool(n_workers) as pool:
                        frames = []
                        for frame in pool.imap(plot_wrapper, args):
                              frames.append(frame)
                  pool.close()
            else:
                  frames = []
                  for arg in args:
                        frames.append(plot_wrapper(arg))
      # Check if all vaues in frames are None
      if all([frame is None for frame in frames]):
            return print('No frames found. Check the input parameters.')

      # Set up the figure for the animation
      fig, ax = plt.subplots(figsize=figsize)
      fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)
      fig.set_size_inches(figsize, forward=True)
      img = ax.imshow(np.zeros((1, 1)), cmap=cmap, aspect='auto', origin='upper')
      ax.axis('off')
      
      interval = 1000  # Interval between frames in milliseconds
      repeat_delay = 5000  # Delay before repeating the animation

      def update(i):
            img.set_data(frames[i])
            return [img]
      # Create the animation
      ani = animation.FuncAnimation(fig, update, frames=len(frames),
                                    interval=interval,
                                    repeat=True,
                                    blit=True, 
                                    repeat_delay=repeat_delay)
      ani_html = ani.to_jshtml()
      plt.close(fig)
      return HTML(ani_html)



