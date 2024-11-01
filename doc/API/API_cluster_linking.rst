Cluster linking
=======================================================

The `cluster_linking` codes contains functions that manage the association of clusters across different frames, ensuring continuity and consistency over time. 
These functions are essential for tracking clusters as they evolve, move, or merge between successive frames.

Key functionalities include:

    * Copying Cluster Indices: Efficiently transfers cluster index values (board_idx) for clusters that interact with the board, ensuring accurate tracking.
    * Temporal Linking: Establishes connections between clusters in the current and previous frames, based on spatial and temporal proximity. This allows for the consistent identification of clusters over time.
    * UID Management: Handles the assignment and updating of global unique identifiers (UIDs) for clusters, ensuring that each cluster is consistently tracked across frames.
    * Trajectory Merging: Combines cluster trajectories from the previous and current frames into unified trajectories, facilitating comprehensive tracking.
    * Cluster UID Refactoring: Updates and refactors UIDs for internal clusters, maintaining the integrity of cluster identities throughout the analysis process.

This suite of functions ensures that clusters are accurately linked and tracked over time, providing a robust framework for analyzing dynamic data in multiple frames.

Board clusters
-------------------------------------------------------

.. autofunction:: pyfortracc.cluster_linking.board_clusters.board_clusters

Cluster linking
-------------------------------------------------------

.. autofunction:: pyfortracc.cluster_linking.cluster_linking.cluster_linking
.. autofunction:: pyfortracc.cluster_linking.cluster_linking.linking

Max uid
-------------------------------------------------------

.. autofunction:: pyfortracc.cluster_linking.max_uid.update_max_uid

Merge trajectory
-------------------------------------------------------

.. autofunction:: pyfortracc.cluster_linking.merge_trajectory.merge_trajectory
.. autofunction:: pyfortracc.cluster_linking.merge_trajectory.merge_lines

New frame
-------------------------------------------------------

.. autofunction:: pyfortracc.cluster_linking.new_frame.new_frame

Refact inside
-------------------------------------------------------

.. autofunction:: pyfortracc.cluster_linking.refact_inside.refact_inside


