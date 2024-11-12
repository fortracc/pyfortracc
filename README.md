# pyForTraCC - Python Library for Tracking and Forecasting Clusters

> **Note**: `pyForTraCC` library is currently in a **release candidate** phase, meaning it is nearly finalized but may receive minor updates before the official stable release.

<!-- badges: start -->
[![stable](https://img.shields.io/badge/docs-stable-blue.svg)](https://pyfortracc.readthedocs.io)
[![pypi](https://badge.fury.io/py/pyfortracc.svg)](https://pypi.python.org/pypi/pyfortracc)
[![Documentation](https://readthedocs.org/projects/pyfortracc/badge/?version=latest)](https://pyfortracc.readthedocs.io/)
[![Downloads](https://img.shields.io/pypi/dm/pyfortracc.svg)](https://pypi.python.org/pypi/pyfortracc)
[![Contributors](https://img.shields.io/github/contributors/fortracc/pyfortracc.svg)](https://github.com/fortracc/pyfortracc/graphs/contributors)
[![License](https://img.shields.io/pypi/l/pyfortracc.svg)](https://github.com/fortracc/pyfortracc/blob/main/LICENSE)
<!-- badges: end -->

## Overview

`pyForTraCC` is a Python library designed to identify and track clusters in diverse datasets, offering flexible integration based on user-defined needs. Its modular structure incorporates specialized methods for feature identification and tracking, allowing for compatibility with various input formats.


### Algorithm Workflow

The algorithm is divided into two main modules: **Track** and **Forecast**.

1. **Track**: This module identifies and tracks clusters in a time-sequenced field. It follows four steps:
   - **Feature Extraction**: Identifies relevant features using multi-thresholding on a time-varying field, clusters contiguous pixels above thresholds, and vectorizes clusters as geospatial objects.
   - **Spatial Operations**: Establishes spatial relationships between features and computes vector displacements between feature centroids.
   - **Cluster Linkage**: Links features across time steps by indexing current features with those from the previous time step, generating unique cluster identifiers, tracking trajectories, and recording the cluster lifetime.
   - **Concatenation**: Combines all identified features and trajectories into a single Parquet file, forming a consolidated tracking table with complete tracking data.

2. **Forecast** (Upcoming): This module will predict future cluster positions through:
   - **Virtual Image**: A persistence-based forecast of cluster positions by shifting clusters in the current time step to a specified future position based on average vector displacement.
   - **Track Routine**: Applies the tracking routine to the virtual image, projecting cluster identification to the anticipated time step.

## Documentation

For detailed instructions and usage, refer to the [pyForTraCC Documentation](https://pyfortracc.readthedocs.io/).

## Installation

Download the package from GitHub or clone the repository:

```bash
git clone https://github.com/fortracc/pyfortracc/
```

It is recommended to use Python 3.12 and a virtual environment (Anaconda3, Miniconda, Mamba, etc.) to avoid dependency conflicts.

### Installing with Conda
Create environment using conda and install from environment.yml file:

```bash
cd pyfortracc
conda env create -f environment.yml
conda activate pyfortracc
```

### Installing with Pip
```bash
pip3 install pyfortracc
```

Running pyFortracc
=====================================================================
To use `pyForTraCC`, install and import the library, then create a custom data-reading function, read_function, tailored to your data’s format. This function should return a two-dimensional matrix as required by the library. Define a dictionary, name_list, with necessary configuration parameters for tracking, including data paths, thresholds, and time intervals. Finally, run the tracking function.

Here is an example script:

```python
import pyfortracc
import xarray as xr

# Custom data reading function
def read_function(path):
    """
    This function reads data from the given path and returns a two-dimensional matrix.
    """
    data = xr.open_dataarray(path).data
    return data

# Parameter dictionary for tracking configuration
name_list = {
    'input_path': 'input/',  # Path to input data
    'output_path': 'output/',  # Path to output data
    'thresholds': [20, 30, 45],  # Intensity thresholds
    'min_cluster_size': [10, 5, 3],  # Minimum cluster size (in number of points)
    'operator': '>=',  # Comparison operator (>=, <=, or ==)
    'timestamp_pattern': '%Y%m%d_%H%M%S.nc',  # Timestamp file naming pattern
    'delta_time': 12  # Time interval between frames, in minutes
}

# Execute tracking with parameters and custom reading function
pyfortracc.track(name_list, read_function)
```

Example Gallery
=====================================================================
To use the library we have a gallery of examples that demonstrate the application of the algorithm in different situations.
The development of this framework is constantly evolving, and several application examples can be seen in our example gallery.

You can run the examples in GitHub Codespaces or Google Colab.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/fortracc/pyfortracc/?quickstart=1)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
[<img src="https://colab.research.google.com/assets/colab-badge.svg" width="170"/>](https://colab.research.google.com/github/fortracc/pyfortracc)



Support and Contact
=====================================================================
- fortracc.project@inpe.br
- helvecio.neto@inpe.br
- alan.calheiros@inpe.br

