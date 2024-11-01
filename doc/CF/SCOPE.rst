Identification Scope
=======================================================

The algorithm's primary goal is to identify the morphological characteristics of rain cells, such as shape, size, and inner clusters. 
This is achieved through segmentation of radar images, using thresholding to highlight regions of interest—a process known as image segmentation [1]_. 
The clusters are defined based on contour thresholds of the rain cells, consistent with other studies that describe the morphological traits of 
precipitating systems in the Amazon [2]_ [3]_ [4]_ [5]_. These studies observed rain cells with radar reflectivity thresholds ranging from 20 dBZ (including both 
stratiform and convective precipitation) to 35 dBZ (mainly convective precipitation). In this context, multi-threshold parameters were selected 
to represent rain cell boundaries, with thresholds of 20, 30, and 35 dBZ, and inner thresholds of 30, 35, and 40 dBZ, as well as 35, 40, and 45 dBZ 
for further inner regions.

The clustering method then categorizes segmented points after thresholding, labeling rain cells for each observation. The algorithm applies DBSCAN 
(Density-Based Spatial Clustering of Applications with Noise), a machine learning technique, to identify clusters (rain cells). It uses a radius 
distance (Eps) and a minimum number of neighboring points to form clusters. 

Finally, the vectorization method transforms clustered rain pixels from matrix format into vector-based polygons, facilitating spatial operations 
like overlap and intersection between geometries of consecutive time frames, making analysis of rain events more manageable.

.. [1] Doyle, W. Operations useful for similarity-invariant pattern recognition. J. ACM (JACM) 1962, 9, 259–267.
.. [2] Laurent, H.; Machado, L.A.; Morales, C.A.; Durieux, L. Characteristics of the Amazonian mesoscale convective systems observed from satellite and radar during the WETAMC/LBA experiment. J. Geophys. Res. Atmos. 2002, 107, LBA-21.
.. [3] Machado, L.A.; Calheiros, A.J.; Biscaro, T.; Giangrande, S.; Silva Dias, M.A.; Cecchini, M.A.; Albrecht, R.; Andreae, M.O.; Araujo, W.F.; Artaxo, P.; et al. Overview: Precipitation characteristics and sensitivities to environmental conditions during GoAmazon2014/5 and ACRIDICON-CHUVA. Copernic. GmbH Atmos. Chem. Phys. 2018, 18, 6461–6482.
.. [4] Nunes, A.M.P.; Silva Dias, M.A.F.; Anselmo, E.M.; Morales, C.A. Severe convection features in the Amazon Basin: A TRMM-based 15-year evaluation. Front. Earth Sci. 2016, 4, 37.
.. [5] Eichholz, C.W. Kinematic and Dynamic Analysis of Rain and Cloud Cells Propagation. Ph.D. Thesis, Instituto Nacional de Pesquisas Espaciais, Sao Jose dos Campos, Brazil, May 2017. Available online: http://urlib.net/rep/8JMKD3MGP3W34P/3NQ5D2P (accessed on 10 August 2022).


