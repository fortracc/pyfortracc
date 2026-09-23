Examples
=======================================================

The Jupyter notebooks below show pyForTraCC with different kinds of data. Each one can be opened in
Google Colab and run in the browser, with no local installation.

.. list-table::
   :header-rows: 1
   :widths: 35 45 20

   * - Notebook
     - Content
     - Link
   * - **1. Introducing pyForTraCC**
     - Synthetic reflectivity cells: read function, name list, tracking, tracking table and
       visualization.
     - `Open in Colab <introducing_colab_>`_
   * - **2. Track Radar Data**
     - S-band radar of Manaus (GoAmazon2014/5), step-by-step algorithm workflow, multiple
       thresholds and vector corrections.
     - `Open in Colab <radar_colab_>`_
   * - **3. Track Infrared Data**
     - GOES-16 channel 13 brightness temperature over South America, tracking of convective
       systems (``operator = '<='``).
     - `Open in Colab <infrared_colab_>`_
   * - **4. Track Global Precipitation**
     - Global precipitation (GSMaP) during hurricane Milton, clusters crossing the domain
       border (``edges = True``).
     - `Open in Colab <precipitation_colab_>`_

Short course (WORCAP, in Portuguese)
-------------------------------------------------------

Notebooks from the pyForTraCC short course held at WORCAP/INPE:

* **Basic tracking** with the synthetic ``bubble_simulation`` dataset: `Open in Colab <worcap1_colab_>`_
* **Real-time tracking** of mesoscale convective systems with GOES-19 brightness temperature,
  including identification of the municipalities with active systems: `Open in Colab <worcap2_colab_>`_
* **Anthropogenic tracking**: land cover change (deforestation) with MapBiomas: `Open in Colab <worcap3_colab_>`_

To run the complete workflow locally in a few minutes, see :doc:`BI_QUICKSTART`.

.. _introducing_colab: https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/01_Introducing_Example/01_Introducing-pyFortraCC.ipynb
.. _radar_colab: https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/02_Track-Radar-Data/02_Track-Radar-Dataset.ipynb
.. _infrared_colab: https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/03_Track-Infrared-Dataset/03_Track-Infrared-Dataset.ipynb
.. _precipitation_colab: https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/04_Track-Global-Precipitation-EDA/04_Track-Global-Precipitation.ipynb
.. _worcap1_colab: https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/WORCAP-Minicourse/1_Basic_Tracking/1_Basic_Tracking.ipynb
.. _worcap2_colab: https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/WORCAP-Minicourse/2_RealTime_Tracking/2_RealTime_Tracking.ipynb
.. _worcap3_colab: https://colab.research.google.com/github/fortracc/pyfortracc/blob/main/examples/WORCAP-Minicourse/3_Antropogenic_Tracking/3_Antropogenic_Tracking.ipynb
