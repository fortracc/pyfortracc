"""
pyfortracc
=====

Provides
    1. Tracking Non-Rigid Clusters in 2D matrix
    2. Forecasting the movement of the Clusters by extrapolation
    3. Plot and analysis of the results of the tracking and forecasting
    4. Visualizing the results of the tracking, validation and forecasting

How to use the package
----------------------------
Documentation is available in two forms: docstrings provided
with the code, and a reference guide, available from
`the project homepage <https://pyfortracc.readthedocs.io/>`.


Available modules
---------------------
track
    Tracking Non-Rigid Clusters in 2D matrix
forecast
    Forecasting the movement of the Clusters by extrapolation


Available subpackages
-----------------
feature_extraction
    Extracting features from the input data
spatial_operations
    Spatial operations on the features
cluster_linking
    Linking the clusters
spatial_conversions
    Converting the results of the tracking or forecasting to spatial data
plot
    Visualizing the results of the tracking, validation and forecasting


About the package
-----------------------------
pyForTraCC is a Python package designed to identify, track, forecast and analyze clusters moving in a time-varying field.
It offers a modular framework that incorporates different algorithms for feature identification, tracking, and analyses.
One of the key advantages of pyForTraCC is its versatility, as it does not depend on specific input variables or a particular grid structure.
In its current implementation, pyForTraCC identifies individual cluster features in a 2D field by applying a specified threshold value.

By utilizing a time-varying 2D input images and a specified threshold value, pyForTraCC can determine the associated volume for these features. The 
software then establishes consistent trajectories that represent the complete lifecycle of a single cell of feature through the tracking step. 
Furthermore, pyForTraCC provides analysis and visualization methods that facilitate the utilization and display of the tracking results.

This algorithm was initially developed and used in the publication "Impact of Multi-Thresholds and Vector Correction for Tracking Precipitating 
Systems over the Amazon Basin" (https://doi.org/10.3390/rs14215408). The methods presented in the research paper have enabled the implementation of robust techniques for extracting the motion vector 
field and trajectory of individual clusters of precipitating cells. These techniques have been applied to the Amazon Basin, where the tracking of 
precipitating systems is essential for understanding the hydrological cycle and its impacts on the environment and used in this algorithm

For further information on pyForTraCC, its modules, and the continuous development process, please refer to the official documentation and stay tuned for updates 
from the community.

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