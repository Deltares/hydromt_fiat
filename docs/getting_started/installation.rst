.. _installation_guide:

==================
Installation guide
==================

# TODO complete according to HydroMT and HydroMT-Wflow docs (e.g. dependencies etc.)

#TODO update if hydromt_fiat on conda-forge

Prerequisites
=============
For more information about the prerequisites for an installation of the HydroMT package and related dependencies, please visit the
documentation of `HydroMT core <https://deltares.github.io/hydromt/latest/getting_started/installation.html#installation-guide>`_

Installation
============

The HydroMT-FIAT plugin is currently only available from PyPi.

.. Note::

    We are working on a release from conda-forge.

If you haven't installed the `HydroMT core package <https://github.com/Deltares/hydromt>`_
we recommend installing it from conda-forge to get all dependencies and then install the plugin. 
Imformation about how to install the HydroMT core can be found `here <https://deltares.github.io/hydromt/latest/getting_started/installation.html>`_.

To install HydroMT-FIAT using pip do:

.. Note::

    Make sure this is installed in the same environment as hydromt.

.. code-block:: console

  $ pip install hydromt_fiat

The HydroMT core and fiat plugin can be easily installed together in a single HydroMT-FIAT environment
using the environment.yml file in the repository binder folder. This environment includes some packages that are 
required to run the example notebooks.

.. code-block:: console

  $ conda env create -f binder/environment.yml
  $ conda activate hydromt-fiat
  $ pip install hydromt_fiat


Developer install
=================

To be able to test and develop the HydroMT-FIAT package see instructions in the :ref:`Developer installation guide <dev_env>`.

