Data Input
=======================================================

The **pyForTraCC** package is designed to work with various types of input data, enabling the identification, tracking, and 
analysis of hydrological features across different datasets. Below are the types of input data that can be used with the package:

    - **NetCDF Format**: The dataset for some examples consists of files in the NetCDF format. This data is a synthetic set created to simulate the movement of cells in a 2D domain, with each cell's values representing reflectivity, akin to radar reflectivity.

    - **Radar Data**: The S-Band Radar located in Manaus, AM, Brazil. The data, processed and published by Schumacher, Courtney, and Funk, Aaron (2018), is available in full on the ARM platform. It is part of the GoAmazon2014/5 project and is titled "Three-dimensional Gridded S-band Reflectivity and Radial Velocity from the SIPAM Manaus S-band Radar dataset."

    - **GOES-16 Satellite Data**: The GOES-16 satellite data from Channel 13 represents infrared channel information, which has been reprojected onto a rectangular grid over South America. This reprocessing ensures the data is more accessible for various applications, including weather forecasting and environmental monitoring.

    - **Global Precipitation System**: This input utilizes JAXA's Global Satellite Mapping of Precipitation (GSMAP) data, which provides precipitation estimates across the globe.

    - **SCaMPR Rainfall Rate Product**: The Self-Calibrating Multivariate Precipitation Retrieval (SCaMPR) rainfall rate product (RRQPE) is available every 10 minutes and covers the entire Earth.

These diverse datasets enable users to leverage the capabilities of the pyForTraCC package effectively, allowing for comprehensive 
tracking and analysis of hydrological features.
