Tracking
=======================================================

Tracking Routine
--------------------------------------------------------

The tracking module encompasses the primary objectives of the algorithm. This module utilizes the tracking parameters and the data reading function, which together facilitate the entire tracking process for the objects present in the input data. The output of this module consists of tracking files, which are stored in the `trackingtable` directory, named after the entity discussed in the subsequent topic. It is important to note that each step of the tracking module incorporates other modules (Feature Extraction, Spatial Operations, Cluster Linking, and Result Containment) dedicated to the object tracking process.

Here is the Python code for tracking:

.. code-block:: python

    # You can also execute all functions in one line using the track function.
    # Note: The parallel option is not available for Mac OS in Jupyter Notebook, 
    # but it works in the terminal when using __name__ == '__main__'.
    pyfortracc.track(name_list, read_function, parallel=False)

.. figure:: image/tracking_process.png
    :align: center
    :alt: Figure 1

Tracking Table
--------------------------------------------------------

The tracking table serves as the generalized output entity of the algorithm. It consists of a collection of files (.parquet) located in the output directory of the same name (`output_path/trackingtable`). The information gathered during the tracking process is stored in a tabular format and is organized according to tracking time. Below are the names of the columns (output variables) and their respective meanings:

- Each row in the tracking table corresponds to a cluster at its designated threshold level.
- The information encompasses unique identifiers, descriptive statistics, geometric properties, and temporal features.
- The structure of the tracking table provides a comprehensive overview of grouped entities, facilitating analysis and understanding of patterns across different threshold levels.

**Tracking Table Columns:**

- `timestamp` (datetime64[us]): Temporal information of the cluster.
- `uid` (float64): Unique identifier of the cluster.
- `iuid` (float64): Internal unique identifier of the cluster.
- `threshold_level` (int64): Level of the threshold.
- `threshold` (float64): Specific threshold value.
- `status` (object): Status of the entity (NEW, CONTINUOUS, SPLIT, MERGE, SPLIT/MERGE).
- `u_`, `v_` (float64): Vector components.
- `inside_clusters` (object): Number of inside clusters.
- `size` (int64): Cluster size in pixels.
- `min`, `mean`, `max`, `std` (float64): Descriptive statistics.
- `delta_time` (timedelta64[us]): Temporal variation.
- `file` (object): Name of the associated file.
- `array_y`, `array_x` (object): Cluster array coordinates.
- `vector_field` (object): Associated vector field.
- `trajectory` (object): Cluster's trajectory.
- `geometry` (object): Geometric boundary representation of the cluster.
- `lifetime` (int64): Lifespan of the cluster in minutes.
- `duration` (int64): Duration of the cluster in minutes.
- `genesis` (int64): Cluster genesis status, where genesis: 1, active: 0, and death: -1.

For more information and details, please refer to the examples section.