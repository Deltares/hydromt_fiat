.. _installation:

============
Installation
============

User install
------------

For Use HydroMT-FIAT, do:
Hydromt-FIAT can be installled in an existing environment or the user can create a new environment. We recommened to create a new environment to avoid issues with other dependencies and packages.

New environment
To create a new environment follow the steps below.

1. Create a new environment:

.. code-block:: console
    
    conda create -n hydromt_fiat python=3.11.*

2. Activate the environment:

.. code-block:: console
    
    conda activate hydromt_fiat

3. Install conda-forge gdal.

.. code-block:: console
    
    conda install -c conda-forge gdal

4. Install Hydromt-FIAT from Github. After creating the new environment, you need to install all dependencies from the Deltares Github repository. You can use **pip install** to do so:

.. code-block:: console
    
    pip install git+https://github.com/Deltares/hydromt_fiat.git

Existing environment
If you want to install FIAT into an existing environment, simply activate the desired environment and run:

.. code-block:: console
    
    pip install git+https://github.com/Deltares/hydromt_fiat.git


Developer install
------------------
For developing on HydroMT-FIAT, do:

.. code-block:: console

  conda env create -f envs/hydromt-fiat-dev.yml
  conda activate hydromt-fiat-dev
  pip install -e .


For more information about how to contribute, see `HydroMT contributing guidelines <https://deltares.github.io/hydromt/latest/dev/contributing>`_.
