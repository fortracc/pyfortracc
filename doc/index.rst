pyForTraCC - Python Library for Tracking and Forecasting Configurable Clusters
=======================================================

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

The algorithm is divided into two main routines Track and Forecast. 

1. **Track**: The tracking routine is responsible for identifying and tracking the clusters in a time-varying field. This routine is divided into four main steps: 
  - **Features Extraction**: The first step is to identify the features in a time-varying field. The features are identified by applying a multi-thresholding technique to the field, clustering the contiguous pixels with values above the threshold and vectorizing the clusters into a geospatial object.
  - **Spatial Operations**: The second step is to perform spatial operations on the features. The spatial operations are used to identify the spatial relationships between the features and create a vector displacement between the centroids of the features.
  - **Cluster Linkage**: The third step is to link the features between the time steps. The linkage is performed by indexing the features in the current time step with the features in the previous time step and create a unique identifier for each cluster that is maintained throughout the tracking process. Additionally, the algorithm creates a trajectory for each cluster and a lifetime of the cluster.
  - **Concatenation**: The fourth step is to concatenate the features and trajectories into a single parquet file. The parquet file contains enteire tracking information of the clusters. And a create a generalized track entity called `tracking table` that contains all information of track process.

2. **Forecast**: The forecasting routine is responsible for predicting the future position of the clusters. This routine is a loop that iterates over the time steps and performs two main steps:
  - **Virtual Image**: The first step is to create a virtual image based persistence forecast of individual clusters. The virtual image is created by shifting the clusters in the current time step to the `n` time steps ahead. The extrapolation is performed by applying a mean vector displacement of the clusters based on u and v components.
  - **Track Routing**: The second step uses a `Track Routine` to identify the clusters in the virtual image. The track routine is applied to the virtual image to identify the clusters in the future time step.  


For further information on pyForTraCC, its modules, and the continuous development process, please refer to the official documentation and stay tuned for updates 
from the community.

.. note::
   This guide for the pyfortrac package is currently under development and will be continuously updated and improved. If you encounter any errors or issues, 
   please don't hesitate to reach out to Helvecio Neto or Alan Calheiros for assistance. Thank you for your understanding and support as we work to enhance this 
   resource.

.. toctree::
   :caption: Basic Information
   :maxdepth: 3

   BI/BI_INSTALL
   BI/BI_DATA
   BI/BI_NAMELIST
   BI/BI_TRACKING
   BI/BI_FORECAST
   BI/BI_UTILITIES
   BI/BI_EXAMPLES
   BI/BI_PUBLICATIONS
   BI/BI_CONTACT

.. toctree::
   :caption: Conceptual Framework
   :maxdepth: 2

   CF/ALGORITHM
   CF/SCOPE
   CF/TRACKING
   CF/CORRECTION

.. toctree::
   :caption: API Reference
   :maxdepth: 2

   API/API_MODULES
