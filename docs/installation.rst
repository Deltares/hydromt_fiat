Installation
============

User install
------------

The hydromt_fiat plugin is currently only available from PyPi.
We are working on a release from conda-forge. 

If you haven't installed the `hydroMT core package <https://github.com/Deltares/hydromt>`_ 
we recommend installing it from conda-forge to get all dependencies and then install the plugin. 

To install hydromt and the toml package using conda-forge do:

.. code-block:: console

  conda install hydromt -c conda-forge

To install hydromt_fiat using pip do:
Note: make sure this is installed in the same environment as hydromt.

.. code-block:: console

  pip install hydromt_fiat

The hydroMT core and fiat plugin can be easily installed together in a single hydromt-fiat environment 
using the environment.yml file in the repository binder folder. This environment includes some packages that are 
required to run the example notebooks.

.. code-block:: console

  conda env create -f binder/environment.yml
  conda activate hydromt-fiat
  pip install hydromt_fiat


Developper install
------------------
If you want to download the fiat plugin directly from git to easily have access to the latest developments or 
make changes to the code you can use the following steps.

First, clone hydromt's fiat plugin ``git`` repo from
`github <https://github.com/Deltares/hydromt_fiat>`_, then navigate into the 
the code folder (where the envs folder and pyproject.toml are located):

.. code-block:: console

    $ git clone https://github.com/Deltares/hydromt_fiat.git
    $ cd hydromt_fiat

Then, make and activate a new hydromt-fiat conda environment based on the envs/hydromt-fiat.yml
file contained in the repository:

.. code-block:: console

    $ conda env create -f envs/hydromt-fiat.yml
    $ conda activate hydromt-fiat

Finally, build and install an editable version of hydromt_fiat using `flit <https://flit.readthedocs.io/en/latest/>`_.

For Windows:

.. code-block:: console

    $ flit install --pth-file

For Linux:

.. code-block:: console

    $ flit install -s

For more information about how to contribute, see `HydroMT contributing guidelines <https://hydromt.readthedocs.io/en/latest/contributing.html>`_.
