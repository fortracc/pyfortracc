"""
pyfortracc
=====

Provides
    1. Tracking Hydrological Non-Rigid Clusters in 2D matrix
    2. Validating the advective movement of the Clusters 
    3. Forecasting the movement of the Clusters by extrapolation
    4. Plot and analysis of the results of the tracking and forecasting
    5. Visualizing the results of the tracking, validation and forecasting

How to use the package
----------------------------
Documentation is available in two forms: docstrings provided
with the code, and a reference guide, available from
`the project homepage <https://pyfortracc.readthedocs.io/>`.


Available modules
---------------------
track
    Tracking Hydrological Non-Rigid Clusters in 2D matrix
validation
    Validating the advective movement of the Clusters
forecast
    Forecasting the movement of the Clusters by extrapolation
concat
    Processing the results of the tracking or forecasting into a single file


Available subpackages
-----------------
feature_extraction
    Extracting features from the input data
spatial_operations
    Spatial operations on the features
trajectory_linking
    Linking the features in time
spatial_conversions
    Converting the results of the tracking or forecasting to spatial data
plot
    Visualizing the results of the tracking, validation and forecasting


About the package
-----------------------------
pyFortraCC: A Python Package for Hydrological Feature Identification,
Tracking, Analysis and Forecasting. pyFortraCC is a Python package designed to 
identify, track, analyze and forecast hydrological phenomena across a diverse 
range of datasets.  It offers a robust modular framework that seamlessly 
integrates various cutting-edge algorithms for feature identification, tracking,
and comprehensive analyses. One of pyFortraCC paramount advantages lies in its
remarkable versatility, which liberates it from any reliance on specific input
variables or grid structures. In its present implementation, pyFortraCC discerns
individual hydrological features by locating maxima or minima in a 
two-dimensional time-varying field  (refer to the “Feature Detection Overview”
section in the documentation).
Through the utilization of time-varying 2D input images alongside a
user-specified threshold value, pyFortraCC adeptly calculates the associated
volume for these identified features, as detailed in the “Segmentation”
section of the documentation.This algorithm was inspired by the research
presented in the publication titled “Impact of Multi-Thresholds and Vector
Correction for Tracking Precipitating Systems over the Amazon Basin”
`<https://doi.org/10.3390/rs14215408>`. Subsequently, the software apply
constructs consistent trajectories that meticulously depict the entire
lifecycle of a single feature cell during the tracking phase. Moreover,
pyFortraCC offers a comprehensive suite of analysis and visualization
tools that greatly facilitate the utilization and presentation of the 
tracking results.

"""

from ._version import __version__
from .default_parameters import default_parameters
from pyfortracc.track import track
from pyfortracc.forecast import forecast
from pyfortracc.features_extraction import features_extraction
from pyfortracc.spatial_operations import spatial_operations
from pyfortracc.cluster_linking import cluster_linking
from .concat import concat
from pyfortracc.plot.plot import plot
from pyfortracc.plot.plot_animation import plot_animation
from pyfortracc.spatial_conversions import spatial_conversions