.. image:: https://mybinder.org/badge_logo.svg
    :target: https://mybinder.org/v2/gh/Deltares/hydromt_fiat/main?urlpath=lab/tree/examples

This folder contains several ipython notebook examples for **HydroMT-FIAT**. 
To run these examples start with the **binder** badge above.

To run these examples on your local machine create a conda environment based on the
hydromt-fiat-dev.yml in the root of this repository and then start jupyter notebook.
Run the following steps from the repository root:

.. code-block:: console

  conda env create -f envs/hydromt-fiat-dev.yml
  conda activate hydromt-fiat-dev
  pip install -e .
  jupyter notebook