pyForTraCC - Python Library for Tracking and Forecasting Clusters
=======================================================

pyForTraCC is a Python package designed to identify, track, and analyze hydrological features in various types of datasets.
It offers a modular framework that incorporates different algorithms for feature identification, tracking, and analyses.
One of the key advantages of pyForTraCC is its versatility, as it does not depend on specific input variables or a particular grid structure.
In its current implementation, pyForTraCC identifies individual hydrological features by locating maxima or minima in a two-dimensional time-varying field.

By utilizing a time-varying 2D input images and a specified threshold value, pyForTraCC can determine the associated volume for these features. The 
software then establishes consistent trajectories that represent the complete lifecycle of a single cell of feature through the tracking step. 
Furthermore, pyForTraCC provides analysis and visualization methods that facilitate the utilization and display of the tracking results.

This algorithm was initially developed and used in the publication "Impact of Multi-Thresholds and Vector Correction for Tracking Precipitating 
Systems over the Amazon Basin" (https://doi.org/10.3390/rs14215408). The methods presented in the research paper "Impact of Multi-Thresholds and Vector 
Correction for Tracking Precipitating Systems over the Amazon Basin" have enabled the implementation of robust techniques for extracting the motion vector 
field and trajectory of individual clusters of precipitating cells. These techniques play a crucial role in accurately identifying and analyzing precipitation 
systems.

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
