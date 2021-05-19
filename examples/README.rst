.. image:: https://mybinder.org/badge_logo.svg
    :target: https://mybinder.org/v2/gh/Deltares/hydromt_fiat/main?urlpath=lab/tree/examples

TODO: This folder contains several ipython notebook examples for **hydroMT-fiat**. 

To run these examples start with the **binder** badge above.

To run these examples on your local machine create a conda environment based on the
environment.yml in the root of this repository and then start jupyter notebook.
Run the following steps from the repository root:

.. code-block:: console

  conda env create -f binder/environment.yml
  conda activate hydromt-fiat
  pip install hydromt_fiat
  jupyter notebook