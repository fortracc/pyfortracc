Modules Description
####################################################

Cluster linking
****************************************************

The `pyfortracc.cluster_linking` codes contains functions that manage the association of clusters across different frames, ensuring continuity and consistency over time. 
These functions are essential for tracking clusters as they evolve, move, or merge between successive frames.

Key functionalities include:
    * Copying Cluster Indices: Efficiently transfers cluster index values (board_idx) for clusters that interact with the board, ensuring accurate tracking.
    * Temporal Linking: Establishes connections between clusters in the current and previous frames, based on spatial and temporal proximity. This allows for the consistent identification of clusters over time.
    * UID Management: Handles the assignment and updating of global unique identifiers (UIDs) for clusters, ensuring that each cluster is consistently tracked across frames.
    * Trajectory Merging: Combines cluster trajectories from the previous and current frames into unified trajectories, facilitating comprehensive tracking.
    * Cluster UID Refactoring: Updates and refactors UIDs for internal clusters, maintaining the integrity of cluster identities throughout the analysis process.

This suite of functions ensures that clusters are accurately linked and tracked over time, providing a robust framework for analyzing dynamic data in multiple frames.

Features extraction
****************************************************

The `pyfortracc.feature_extraction` codes encompasses functions dedicated to deriving meaningful insights from the data by identifying and calculating various 
features and statistics related to clusters.

Key functionalities include:
    * Cluster Labeling: Assigns cluster labels to each data point based on the clustering method employed, enabling the identification of cluster membership across the dataset.
    * Feature Extraction: Computes relevant features from the data, providing a detailed characterization of each cluster's properties.
    * Feature Calculation: Processes individual data files to extract and calculate features specific to the clusters within that file.
    * Cluster Statistics: Computes statistical measures for each cluster, offering a deeper understanding of the cluster's characteristics and behaviors.

This module serves as the foundation for analyzing and interpreting the structure and dynamics of clusters within the dataset.

Forecast
****************************************************

The `pyfortracc.forecast` codes extrapolate the tracked clusters to the next time steps (nowcasting).

Key functionalities include:

    * Forecast Generation: Reads the last frames of the tracking table before the forecast time, builds a virtual image for each lead time and processes it with the tracking routine, producing a forecast table with the same structure as the tracking table.
    * Persistence Method: Computes the mean displacement vector of each cluster over the observation window and shifts the cluster pixels along it.
    * Forecast Outputs: Saves the virtual images as NetCDF files, the forecast table as parquet files and the forecast cluster boundaries as GeoJSON.

The only forecast mode currently available is persistence. See :doc:`../BI/BI_FORECAST` for a guide.

Plot
****************************************************

The `pyfortracc.plot` codes contains functions aimed at visualizing tracking data through static and animated plots, providing an essential tool for interpreting and presenting geospatial or raster data.

Key functionalities include:

    * Animated Plot Generation: Creates animated visualizations from geospatial or raster data, enabling dynamic representation of data changes over time.
    * Tracking Data Visualization: Generates visual representations of tracking data, either on a map or as a simple 2D plot, facilitating the understanding of spatial patterns and movement.

This module is key to transforming raw data into meaningful visualizations, allowing for clear and intuitive analysis of spatial and temporal trends.

Post processing
****************************************************

The `pyfortracc.post_processing` codes enrich and export the tracking table after the tracking.

Key functionalities include:

    * Cluster Duration: Computes the total duration of each cluster and marks its first and last frames (DuckDB based).
    * Raster Integration: Extracts values and zonal statistics from external gridded data inside each cluster.
    * Vector Integration: Labels each cluster with an attribute of the polygon of a vector file with the largest intersection.
    * Rasterization: Converts columns of the tracking table and the displacement vectors into NetCDF grids.
    * Legacy Format: Exports the tracking to the text "family" format of the original ForTraCC algorithm.

See :doc:`../BI/BI_POSTPROCESSING` for a guide.


Spatial conversions
****************************************************

The `pyfortracc.spatial_conversion group` codes focused on processing and converting geospatial tracking data into various formats and applying necessary transformations. This module is crucial for managing and converting spatial data to facilitate further analysis and visualization.

Key functionalities include:

    * Boundary Extraction and Translation: Processes geospatial tracking data to extract and translate the boundaries of tracked objects within a specified time range, saving the boundaries in the desired format.
    * Velocity and Angle Calculation: Analyzes single parquet files to compute velocity and angle vectors, transforms geometries, and saves the processed data in a specified format.
    * Cluster Data Extraction: Extracts and organizes cluster data from parquet files and saves it as NetCDF files, ensuring compatibility with other data processing workflows.
    * Spatial Data Processing: Manages spatial data processing by invoking various sub-functions for different spatial conversions, streamlining complex conversion tasks.
    * Trajectory Data Translation: Translates and saves trajectory data from Parquet files, either within a specified time range or after applying geotransformations, ensuring accurate and up-to-date trajectory information.
    * Vector Field Data Translation: Translates and saves vector field data from Parquet files, applying geotransformations as needed and saving in the specified format.

This module is essential for converting and transforming spatial data into formats suitable for further analysis, ensuring that data is accurately processed and preserved throughout various stages of the workflow.

Spatial operations
****************************************************

The `pyfortracc.spatial_operations` codes provides functions for performing and managing spatial operations between consecutive feature files, facilitating the analysis of cluster dynamics and interactions across frames.

Key functionalities include:

    * Dataframe Operations: Performs various operations between two dataframes, such as counting clusters, overlaying, and linking, to analyze and compare spatial data.
    * Cluster Analysis: Identifies and retrieves information about continuous, merging, and splitting clusters, providing insights into cluster behavior and transitions.
    * Edge Detection: Checks if clusters in the current dataframe are touching the left or right edge, helping to understand boundary interactions.
    * Spatial Computations: Processes spatial operations for given files, including computing cluster details, trajectories, and vector fields, ensuring comprehensive spatial analysis.
    * Validation and Extrapolation: Validates correction methods by comparing current and previous frames and extrapolates previous clusters to the current frame, assessing the accuracy of spatial corrections.

This module is essential for detailed spatial analysis, enabling the examination of cluster evolution and interactions across multiple frames.

Utilities
****************************************************

The `pyfortracc.utilities` codes provides a diverse set of functions designed to support various calculations, data transformations, and file management tasks essential for spatial and geospatial data processing.

Key functionalities include:

    * Radar and Hydrometeor Conversions: Converts radar reflectivity (dBZ) to volume concentration (mm²/m³) and vice versa, as well as converting between radar reflectivity and rainfall rate (mm/h) using the Marshall-Palmer formula.
    * Vector and Magnitude Calculations: Computes zonal (u) and meridional (v) components, calculates vector magnitudes, angles, and the mean of vector components, and determines angles and magnitudes between points.
    * Geospatial Transformations: Calculates geotransform parameters, transforms features in trajectories, and adjusts geometries to handle cases such as longitudes exceeding 180 degrees. Supports parallel processing for efficiency.
    * Data Format Conversion: Converts trajectory features from Parquet to GeoJSON format and cluster features from Parquet to NetCDF format.
    * File Management: Retrieves lists of files or specific types (e.g., .parquet), organizes files for processing, and creates necessary directories. Includes functions for progress tracking, timestamp extraction, and generating domain edges.
    * DataFrame Operations: Creates and manages DataFrames with specified schemas, reads and writes Parquet files with optional compression, and sets parameters for worker processes and memory usage.

This module is focus in performing fundamental calculations, handling spatial transformations, managing file operations, and preparing data for further analysis.

Vector methods
****************************************************

The `pyfortracc.vector_methods` group provides a collection of functions designed for advanced image processing and optical flow analysis, as well as for managing and generating vectors from specific event types.

Key functionalities include:

    * Event-Based Vector Creation:

        - Generates vectors from events with inner cores, merged cells, and split cells, based on their spatial components.

    * Image Processing Techniques:

        - Noise and Blurring: Adds Gaussian noise to images, applies Gaussian blur for smoothing, and sharpens images using a Laplacian kernel.
        - Intensity and Transformation: Scales image intensity, applies Z-score transformation, and performs histogram equalization to enhance contrast.
        - Thresholding and Filtering: Applies image thresholding to create binary or segmented images, performs median filtering to reduce noise, and uses dilation and erosion for morphological operations.
        - Edge and Texture Detection: Performs Canny edge detection and texture analysis using a Gabor filter.

    * Optical Flow Analysis:

        - Calculates optical flow between two frames using various methods, including the Lucas-Kanade and Farneback methods, to analyze movement and changes between frames.

    * Image Normalization and Segmentation:
    
        - Segments images based on specified operators, normalizes image matrices to a range of 0 to 255, and applies histogram equalization for improved image quality.

This module is integral for sophisticated image manipulation, optical flow computation, and vector management, enabling detailed analysis and enhancement of spatial and temporal image data.
