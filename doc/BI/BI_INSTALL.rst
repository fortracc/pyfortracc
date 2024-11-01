Instalation
=======================================================

To get started with the **pyForTraCC** package, you can download the package from GitHub or clone the repository using the following command:x

.. code-block:: console

    git clone https://github.com/fortracc-project/pyfortracc/

We recommend installing the **pyForTraCC** package with Python 3.12. To simplify the installation process and avoid potential conflicts, it's advisable 
to use a virtual environment (e.g., Anaconda3, Miniconda, Mamba) for managing dependencies. Below are the steps to set up your environment:

Option 1: Install via Conda using environment.yml
****************************************************

    1. Navigate to the cloned pyfortracc directory:

    .. code-block:: console

        cd pyfortracc

    2. Create a new environment and install the required dependencies using the provided environment.yml file:

    .. code-block:: console

        conda env create -f environment.yml

    3. Activate the newly created environment:

    .. code-block:: console

        conda activate pyfortracc

Option 2: Install via pip or Conda
****************************************************

Alternatively, you can install the pyForTraCC package directly using `pip` or `conda`:

    * Using pip:

    .. code-block:: console

        pip3 install pyfortracc

    * Using conda:

    .. code-block:: console

        conda install -c conda-forge pyfortracc


List of requirements
****************************************************

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