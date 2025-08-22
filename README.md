# pyForTraCC - Python library for Forecasting and Tracking the Evolution of Configurable Clusters

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

`pyForTraCC` is a Python library developed for identifying, tracking, and forecasting clusters in diverse datasets. Its modular structure enables flexible integration, supporting user-defined configurations and compatibility with multiple input formats.

### Algorithm Workflow

The algorithm is divided into two main modules: **Track** and **Forecast**.

1. **Track**: This module identifies and tracks clusters in a time-sequenced field. It follows four steps:
   - **Feature Extraction**: Identifies relevant features using multi-thresholding on a time-varying field, clusters contiguous pixels above thresholds, and vectorizes clusters as geospatial objects.
   - **Spatial Operations**: Establishes spatial relationships between features and computes vector displacements between feature centroids.
   - **Cluster Linkage**: Links features across time steps by indexing current features with those from the previous time step, generating unique cluster identifiers, tracking trajectories, and recording the cluster lifetime.
   - **Concatenation**: Combines all identified features and trajectories into a single Parquet file, forming a consolidated tracking table with complete tracking data.

2. **Forecast**: This module will predict future cluster positions through:
   - **Virtual Image**: A persistence-based forecast of cluster positions by shifting clusters in the current time step to a specified future position based on average vector displacement.
   - **Track Routine**: Applies the tracking routine to the virtual image, projecting cluster identification to the anticipated time step.

## Documentation

For detailed instructions and usage, refer to the [pyForTraCC Documentation](https://pyfortracc.readthedocs.io/).

## Installation
The pyForTraCC package can be installed in two ways: Directly by via the `pip` package manager or cloning the official GitHub repository.

#### 1. Installing with Pip (Directly)
To install or update pyForTraCC directly from the Python Package Index (PyPI), use:

```bash
pip install -U pyfortracc
```

#### 2. Installing from GitHub  
Download the package directly from the official GitHub repository by cloning it:

```bash
git clone https://github.com/fortracc/pyfortracc/
```
After downloading, you can install the package directly. It is recommended to use Python 3.12 and a virtual environment (such as Anaconda3, Miniconda, or Mamba) to avoid dependency conflicts.

- **Installing with Conda** If you are using Conda, you can install the package dependencies as follows:
   
   ```bash
   cd pyfortracc
   conda env create -f environment.yml
   conda activate pyfortracc
   ```

- **Installing with pip** Alternatively, you can install the package with `pip`:
   
   ```bash
   cd pyfortracc
   python3 -m venv venv
   source venv/bin/activate  # On Linux/macOS
   .venv\bin\activate  # On Windows
   pip install .
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
To library have a gallery of examples that demonstrate the application of the algorithm in different situations.


You can run the examples in Google Colab:

|                                                                                    | Example                              |
|-------------------------------------------------------------------------------------------|----------------------------------------|
| [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/01_Introducing_Example/01_Introducing-pyFortraCC.ipynb) | 01 - Introducing Example              |
| [![Open in Cola](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/02_Track-Radar-Data/02_Track-Radar-Dataset.ipynb) | 02 - Radar Data Example               |
| [![Open in Cola](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/03_Track-Infrared-Dataset/03_Track-Infrared-Dataset.ipynb) | 03 - Infrared Satellite Example (Realtime Track) |
| [![Open in Cola](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/04_Track-Global-Precipitation-EDA/04_Track-Global-Precipitation.ipynb) | 04 - Global Precipitation Example     |



&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;

 or Github Codespaces: 

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/fortracc/pyfortracc/?quickstart=1)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;




Support and Contact
=====================================================================
- fortracc.project@inpe.br

