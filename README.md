pyForTraCC - Python Library for Tracking and Forecasting Clusters
=====================================================================
<!-- badges: start -->
[![stable](https://img.shields.io/badge/docs-stable-blue.svg)](https://pyfortracc.readthedocs.io)
[![pypi](https://badge.fury.io/py/pyfortracc.svg)](https://pypi.python.org/pypi/pyfortracc)
[![Documentation](https://readthedocs.org/projects/pyfortracc/badge/?version=latest)](https://pyfortracc.readthedocs.io/)
[![Downloads](https://img.shields.io/pypi/dm/pyfortracc.svg)](https://pypi.python.org/pypi/pyfortracc)
[![Contributors](https://img.shields.io/github/contributors/fortracc-project/pyfortracc.svg)](https://github.com/fortracc/pyfortracc/graphs/contributors)
[![License](https://img.shields.io/pypi/l/pyfortracc.svg)](https://github.com/fortracc/pyfortracc/blob/main/LICENSE)
<!-- badges: end -->

Overview
=====================================================================

`pyForTraCC` is a Python package designed to identify, track, and forecasting for several types of datasets. It offers a modular framework that incorporates different algorithms for feature identification, tracking, and forecasting. One of the key advantages of pyForTraCC is its versatility, as it usually does not depend on specific input variables or a particular grid structure.

##### Algorithm Workflow

The algorithm is divided into two main routines Track and Forecast. 

1. **Track**: The tracking routine is responsible for identifying and tracking the clusters in a time-varying field. This routine is divided into four main steps: 
	  - **Features Extraction**: The first step is to identify the features in a time-varying field. The features are identified by applying a multi-thresholding technique to the field, clustering the contiguous pixels with values above the threshold and vectorizing the clusters into a geospatial object.
	  - **Spatial Operations**: The second step is to perform spatial operations on the features. The spatial operations are used to identify the spatial relationships between the features and create a vector displacement between the centroids of the features.
	  - **Cluster Linkage**: The third step is to link the features between the time steps. The linkage is performed by indexing the features in the current time step with the features in the previous time step and create a unique identifier for each cluster that is maintained throughout the tracking process. Additionally, the algorithm creates a trajectory for each cluster and a lifetime of the cluster.
 	 - **Concatenation**: The fourth step is to concatenate the features and trajectories into a single parquet file. The parquet file contains enteire tracking information of the clusters. And a create a generalized track entity called `tracking table` that contains all information of track process.

2. **Forecast** (Soon): The forecasting routine is responsible for predicting the future position of the clusters. This routine is a loop that iterates over the time steps and performs two main steps:
  	- **Virtual Image**: The first step is to create a virtual image based persistence forecast of individual clusters. The virtual image is created by shifting the clusters in the current time step to the `n` time steps ahead. The extrapolation is performed by applying a mean vector displacement of the clusters based on u and v components.
  	- **Track Routing**: The second step uses a `Track Routine` to identify the clusters in the virtual image. The track routine is applied to the virtual image to identify the clusters in the future time step.  


Documentation
=====================================================================
For a more detailed information of `pyForTraCC` package please read the user guide available [Documentation](https://pyfortracc.readthedocs.io/).


Installation
=====================================================================
Download the package from github or clone the repository using the command:

    git clone https://github.com/fortracc/pyfortracc/

We recommend installing the `pyForTraCC` package with Python 3.12. To make things easier and avoid conflicts, 
it's a good idea to use a virtual environment (Anaconda3, Miniconda, Mamba, etc.) for managing dependencies. 
Here are some different ways you can do this:

Create environment using conda and install from environment.yml file:
	
	cd pyfortracc
	conda env create -f environment.yml
	conda activate pyfortracc

 or you can install the the `pyForTraCC` package using pip3 or conda.

 pip install:

 	pip3 install pyfortracc

 conda install:
  
  	conda install -c conda-forge pyfortracc

Running pyFortracc
=====================================================================
To use the `pyfortracc` library, first install and import it in your code. Then, create a custom file-reading function called `read_function`, which should be adjusted according to the specific format of the data you are processing. It is essential that this function returns a two-dimensional matrix, as this is the expected structure for the library. After defining the reading function, create a configuration parameter dictionary called `name_list`, containing the necessary settings for tracking, such as the input and output data paths, intensity thresholds for events, minimum cluster size, comparison operator, timestamp pattern in the files, and the time interval between frames. With the reading function and parameter dictionary configured, simply execute the tracking using `pyfortracc.track`, passing `name_list` and `read_function` as arguments to start processing the data.

Here is the complete code in a single Python routine:

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

[![01 - Introducing Example:](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/01_Introducing_Example/01_Introducing-pyFortraCC.ipynb) - 01 - Track Synthetic data (Introducing Example) 

[![02 - Track Radar Data (GoAmazon Example)](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/02_Track-Radar-Data/02_Track-Radar-Dataset.ipynb) - 02 - Track Radar Data (GoAmazon Example)

[![03 - Track Infrared (Real Time Tracking):](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/03_Track-Infrared-Dataset/03_Track-Infrared-Dataset.ipynb) - 03 - Track GOES16-IR (Real Time Tracking from CPTEC/INPE)

[![04 - Track Global Precipitation (Milton Hurricane):](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/04_Track-Global-Precipitation-EDA/04_Track-Global-Precipitation.ipynb) - 04 - Track GSMAP (Milton Hurricane)

Support and Contact
=====================================================================
For support and contact e-mail:
- fortracc.project@inpe.br
- helvecio.neto@inpe.br
- alan.calheiros@inpe.br
