Tracking
=======================================================

The tracking module utilizes data from two consecutive time points to extract the trajectories of precipitation systems (PSs). 
It identifies the movement of rain cells by analyzing the centroids of these clusters, focusing on areas of overlap between their geometries 
at successive times. This overlap is critical for classifying events into categories such as continuous, splits, and mergers. Although many 
algorithms employ similar methods, variations in centroid positioning due to the defined geometry can affect the computation of velocity and 
position along the trajectory [1]_ [2]_ [3]_. 

To mitigate these issues, smoothing techniques are applied to the shapes of tracked objects, helping to eliminate 
gaps and holes caused by pixel thresholding. Each tracked rain cell is associated with key metrics, including size, expansion rate, average 
reflectivity, centroid coordinates, velocity, and direction, which are essential for establishing its trajectory. A minimum overlap percentage of 
10% is used as a similarity criterion for associating rain cells across time points, allowing the calculation of a displacement vector. The tracking 
process also accounts for merging and splitting behaviors among rain cells, which are influenced by their interactions throughout their life cycles 
and stages of development. The module characterizes these interactions by defining transition events between consecutive times based on specific 
interaction classes.

    * New Rain Cell (NEW): While comparing two successive times, there is no overlap of areas between cell geometries at times :math:`t-1` and :math:`t`. In this situation, it is considered that there was a spontaneous generation of a new system, and a new life cycle is started from a cell at time :math:`t`.

    * Continuous (CON): While comparing two successive times :math:`t-1` and :math:`t`, there is a unique overlap between the geometries of the two cells.

    * Split (SPL): This situation occurs when two or more cells at time :math:`t` overlap with the geometry of a cell at time :math:`t-1`. In this case, a cell with the largest area at time :math:`t` is classified as SPL, and a displacement vector starting from the centroid of cell :math:`t-1` is added to the track. The cell with the smallest area at time :math:`t-1` has its life cycle terminated or proceeds as a new system at the next time.

    * Merge (MRG): The opposite situation to splitting (SPL), where two cells at time :math:`t-1` overlap into just a single cell at time :math:`t`. In this case, the rain cell at time :math:`t` receives the same relational entities as the cell with a larger area at time :math:`t-1`, while the other cell ends its life cycle.

.. [1] Vila, D.A.; Machado, L.A.; Laurent, H.; Velasco, I. Forecast and Tracking the Evolution of Cloud Clusters (ForTraCC) using satellite infrared imagery: Methodology and validation. Weather Forecast. 2008, 23, 233–245.
.. [2] Dixon, M.; Wiener, G. TITAN: Thunderstorm identification, tracking, analysis, and nowcasting—A radar-based methodology. Weather Forecast. 1993, 10, 785–797.
.. [3] Sawant, M.; Shende, M.K.; Feijóo-Lorenzo, A.E.; Bokde, N.D. The State-of-the-Art Progress in Cloud Detection, Identification, and Tracking Approaches: A Systematic Review. Energies 2021, 14, 8119.
