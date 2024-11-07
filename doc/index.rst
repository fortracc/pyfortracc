pyForTraCC - Python Library for Tracking and Forecasting Configurable Clusters
=======================================================

The Forecasting and Tracking the Evolution of Cloud Clusters (ForTraCC) algorithm, introduced by Vila et al. (2008) (https://doi.org/10.1175/2007WAF2006121.1), was a pioneering tool in monitoring and predicting the evolution of cloud clusters, with significant applications in weather forecasting. Building upon this foundation, the Python Forecasting and Tracking the Evolution of Configurable Clusters (pyForTraCC) extends these capabilities with new customization options. The term "configurable" replaces "cloud" to reflect a key enhancement: pyForTraCC allows users to adjust and modify the tracked clusters based on specific configurations or parameters. This flexibility enables tailored definitions and monitoring of clusters, adapting to varying criteria or specific user needs. This added customization makes pyForTraCC a versatile tool for a broader range of tracking and forecasting applications, from precipitation systems to other phenomena.

The development of the pyForTraCC algorithm was driven by the need to create innovative tools for nowcasting – short-term forecasting of atmospheric phenomena – with a focus on precipitation systems. This project aligns directly with Strategic Objective OE-14 from the 2022-2026 Strategic Plan, which aims to maintain INPE’s leadership in cutting-edge science by promoting innovative technologies, products, and services in remote sensing, geospatial data science, environmental science, and geoinformatics, applied to Earth system science studies. The pyForTraCC also supports the strategic milestone M-14.3, which emphasizes the need for meteorological products derived from satellite and radar data, essential for meteorological agencies, governmental decision makers, public and private institutions, and society at large. pyForTraCC contributes to this goal by focusing on weather forecasting with satellite-derived products.

pyForTraCC is a Python package designed to identify, track, and forecasting for several types of datasets. It offers a modular framework that incorporates different algorithms for feature identification, tracking, and forecasting. One of the key advantages of pyForTraCC is its versatility, as it usually does not depend on specific input variables or a particular grid structure.

The algorithm was initially presented in the research paper “Impact of Multi-Thresholds and Vector Correction for Tracking Precipitating Systems over the Amazon Basin” (https://doi.org/10.3390/rs14215408), which details the implementation of robust techniques for extracting the motion vector field and trajectory of clusters of precipitating cells. These techniques play a crucial role in accurately identifying and analyzing precipitation systems, enhancing the ability to monitor and forecast significant weather events with direct impact on nowcasting.


By utilizing a time-varying 2D input images and a specified threshold value, pyForTraCC can determine the associated volume for these features. The software then establishes consistent trajectories that represent the complete lifecycle of a single cell of feature through the tracking step. Furthermore, pyForTraCC provides analysis and visualization methods that facilitate the utilization and display of the tracking results. Also, the forecasting module uses these lifecycle information to predict, by extrapolation, the behavior of the clusters for many lead times.

For further information on pyForTraCC, its modules, and the continuous development process, please refer to the official documentation and stay tuned for updates from the community.

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
