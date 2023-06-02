hydroMT-fiat: FIAT plugin for hydroMT
#########################################

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


hydroMT_ is a python package, developed by Deltares, to build and analyze hydro models.
It provides a generic model api with attributes to access the model schematization,
(dynamic) forcing data, results and states. This plugin provides an implementation 
for the FIAT_ model.


.. _hydromt: https://deltares.github.io/hydromt
.. _FIAT: https://storymaps.arcgis.com/stories/687a256881b94bf6ad20677543bb8cf2


Installation
------------

hydroMT-fiat is available from pypi and will be added to conda-forge (in progress).

To install hydromt_fiat using pip do:

.. code-block:: console

  pip install hydromt_fiat

We recommend installing a hydromt-fiat environment including the hydromt_fiat package
based on the environment.yml file. This environment will install all package dependencies 
including the core of hydroMT_.

.. code-block:: console

  conda env create -f binder/environment.yml
  conda activate hydromt-fiat
  pip install hydromt_fiat

Documentation
-------------

Learn more about the hydroMT_fiat plugin in its `online documentation <https://deltares.github.io/hydromt_fiat/>`_

Contributing
------------

You can find information about contributing to hydroMT at our `Contributing page <https://deltares.github.io/hydromt_fiat/latest/contributing.html>`_.

License
-------

Copyright (c) 2021, Deltares

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General 
Public License as published by the Free Software Foundation, either version 3 of the License, or (at your 
option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the 
implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License 
for more details.

You should have received a copy of the GNU General Public License along with this program. If not, 
see <https://www.gnu.org/licenses/>.
