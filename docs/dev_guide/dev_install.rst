.. _dev_env:

Developer's environment
=======================

If you want to download the FIAT plugin directly from git to easily have access to the latest developments or
make changes to the code you can use the following steps.

First, clone HydroMT's fiat plugin ``git`` repo from
`github <https://github.com/Deltares/hydromt_fiat>`_, then navigate into the
the code folder (where the envs folder and pyproject.toml are located):

.. code-block:: console

    $ git clone https://github.com/Deltares/hydromt_fiat.git
    $ cd hydromt_fiat

Then, make and activate a new HydroMT-FIAT conda environment based on the envs/hydromt-fiat.yml
file contained in the repository:

.. code-block:: console

    $ conda env create -f envs/hydromt-fiat.yml
    $ conda activate hydromt-fiat

Finally, build and install an editable version of HydroMT-FIAT using `flit <https://flit.readthedocs.io/en/latest/>`_.

For Windows:

.. code-block:: console

    $ flit install --pth-file

For Linux:

.. code-block:: console

    $ flit install -s

For more information about how to contribute, see `HydroMT contributing guidelines <https://hydromt.readthedocs.io/en/latest/contributing.html>`_.


