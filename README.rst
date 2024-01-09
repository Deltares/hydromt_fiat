HydroMT-FIAT: HydroMT plugin for Delft-FIAT
############################################

.. image:: https://codecov.io/gh/Deltares/hydromt_fiat/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/Deltares/hydromt_fiat

.. image:: https://img.shields.io/badge/docs-latest-brightgreen.svg
    :target: https://deltares.github.io/hydromt_fiat/latest
    :alt: Latest developers docs

.. image:: https://img.shields.io/badge/docs-stable-brightgreen.svg
    :target: https://deltares.github.io/hydromt_fiat/stable
    :alt: Stable docs last release

.. image:: https://badge.fury.io/py/hydromt_fiat.svg
    :target: https://pypi.org/project/hydromt_fiat/
    :alt: Latest PyPI version

.. image:: https://mybinder.org/badge_logo.svg
    :target: https://mybinder.org/v2/gh/Deltares/hydromt_fiat/main?urlpath=lab/tree/examples


HydroMT_ is a python package, developed by Deltares, to build and analyze hydro models.
It provides a generic model api with attributes to access the model schematization,
(dynamic) forcing data, results and states. This plugin provides an implementation 
for the Delft-FIAT_ model.


.. _hydromt: https://deltares.github.io/hydromt
.. _Delft-FIAT: https://www.deltares.nl/en/software-and-data/products/delft-fiat-flood-impact-assessment-tool


Installation
------------

HydroMT-FIAT is available from pypi and will be added to conda-forge (in progress).

To install hydromt_fiat for usage, do:

.. code-block:: console

  pip install hydromt_fiat

For developing on HydroMT-FIAT, do:

.. code-block:: console

  conda env create -f envs/hydromt-fiat-dev.yml
  conda activate hydromt-fiat-dev
  pip install -e .

Documentation
-------------

Learn more about the HydroMT-FIAT plugin in its `online documentation <https://deltares.github.io/hydromt_fiat/>`_

Contributing
------------

You can find information about contributing to HydroMT at our `Contributing page <https://deltares.github.io/hydromt/latest/dev/contributing>`_.
