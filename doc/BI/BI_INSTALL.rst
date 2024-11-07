Installation
========================================================

Create and environment
--------------------------------------------------------

To streamline the use of **PyForTraCC** and manage dependencies effectively, it's recommended to create a dedicated environment named **pyfortracc**. 
This environment can be created with Anaconda or by using a pip environment, depending on your preferred setup.

Option 1: Using Anaconda or Miniconda
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Anaconda and Miniconda are popular tools for managing data science environments and packages. They provide an isolated setup that ensures 
compatibility between dependencies.

    * Create the environment from the environment.yml file:

    .. code-block:: console

        conda env create -f environment.yml

    * Activate the environment:

    .. code-block:: console

        conda activate pyfortracc

Option 2: Using pip and a Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you prefer using pip, you can create a virtual environment using venv and install the required packages.

    * Create a virtual environment:

    .. code-block:: console

        python3 -m venv pyfortracc

    * Activate the environment in macOS and Linux:

    .. code-block:: console

        source pyfortracc/bin/activate
    
    * Activate the environment in Windows:

    .. code-block:: console

        pyfortracc\Scripts\activate


Install
--------------------------------------------------------
To install PyForTraCC, we recommend using one of the following methods based on your needs. The primary method listed 
ensures that you are using the latest version directly from the official repository, with alternative methods available for convenience.

Recommended Method: Install Latest Version via GitHub
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
For the most up-to-date version of PyForTraCC, we recommend installing directly from the GitHub repository. This method allows you 
to obtain any recent updates or bug fixes made to the package:

.. code-block:: console

    pip3 install --upgrade git+https://github.com/fortracc/pyfortracc.git@main#egg=pyfortracc

This command installs PyForTraCC from the main branch, ensuring you have the latest stable version available.

Alternative Method: Install via Conda
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you prefer to use conda for package management, PyForTraCC is also available through the conda-forge channel. While this version might 
lag slightly behind the latest GitHub version, it is a convenient option for users within the conda ecosystem:

.. code-block:: console

    conda install -c conda-forge pyfortracc

Alternative Method: Install via PyPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
PyForTraCC is available on PyPI as well. This option provides a stable release but may not include the latest features or fixes. To install from PyPI, use:

.. code-block:: console

    pip3 install pyfortracc

Each of these methods will install PyForTraCC, but we strongly recommend the GitHub installation if you want the most current version for 
ongoing developments and improvements.

List of requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The following libraries are required to ensure that PyForTraCC functions optimally. These dependencies support various essential tasks such as 
data handling, geographic and spatial operations, scientific computing, and performance monitoring. Before running the PyForTraCC library, please 
ensure these packages are installed within your environment.

    - rasterio
    - geopandas
    - opencv-python
    - opencv_contrib_python
    - xarray
    - scipy
    - scikit-learn
    - pyarrow
    - pyspark
    - netCDF4
    - cartopy
    - tqdm
    - ipython
    - ipykernel
    - psutil

We recommend installing the **pyForTraCC** package with Python 3.12. To simplify the installation process and avoid potential conflicts, it's advisable 
to use a virtual environment (e.g., Anaconda3, Miniconda, Mamba) for managing dependencies.
