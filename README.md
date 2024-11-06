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

`pyForTraCC` is a Python package designed to identify, track, and analyze hydrological phenomena using various data formats. 
By working with time-varying 2D input frames and user-specified parameters, pyForTraCC can detect objects (clusters) and track their movement over time.
The package also saves tracking files in user-friendly formats, enabling scientific research on various scenarios where the tracked targets are non-rigid objects. 
This makes it easier to study and understand the behavior of these phenomena in different conditions.

##### Algorithm Workflow

The algorithm is divided into three main modules and form the Tracking Workflow. 
<ol>
  <li><b>Feature detection</b>: Focuses on identifying individual clusters detection from individual frame of data and extraction of features and statistics.
  </li>
  <li><b>Spatial Operations</b>: Involves spatial operations (overlap, union, difference, etc) between objects (clusters) from consecutive time steps (t-1 and t).
  <li><b>Trajectory Linking</b>: Link objects of consecutive time steps based on the spatial association.
  </li>

Documentation
=====================================================================
For a more detailed information of `pyForTraCC` package please read the user guide available [click here]([https://link-url-here.org](https://github.com/fortracc/pyfortracc/blob/main/UserGuide.md)).


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

 	pip3 install pyfortracc
  or
  
  	conda install -c conda-forge pyfortracc


Example Gallery
=====================================================================
To use the library we have a gallery of examples that demonstrate the application of the algorithm in different situations.
The development of this framework is constantly evolving, and several application examples can be seen in our example gallery.

[![01 - Introducing Example:](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/01_Introducing_Example/01_Introducing-pyFortraCC.ipynb) - 01 - Introducing Example

[![02 - Track Radar Reflectivity (Algorithm Workflow)](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/02_Algorithm_Workflow_Radar_Example/02_Algorithm_Workflow.ipynb) - 02 - Track Radar Reflectivity (Algorithm Workflow)

[![03 - Track Infrared (Real Time Tracking):](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/03_Track-Infrared-Dataset/03_Track-Infrared-Dataset.ipynb) - 03 - Track Infrared (Real Time Tracking)

[![04 - Track Global Precipitation (Milton Hurricane):](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/04_Track-Global-Precipitation-EDA/04_Track-Global-Precipitation.ipynb) - 04 - Track Global Precipitation (Milton Hurricane)

Support and Contact
=====================================================================
For support, email helvecio.neto@inpe.br, alan.calheiros@inpe.br
