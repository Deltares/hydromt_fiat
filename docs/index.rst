=====================================================================
HydroMT-FIAT: Automated and reproducible Delft-FIAT model building
=====================================================================

With the `HydroMT-FIAT plugin <https://github.com/Deltares/hydromt_fiat>`_, users can easily benefit 
from the rich set of tools of the `HydroMT package <https://github.com/Deltares/hydromt>`_ to build and update 
`Delft-FIAT <https://github.com/Deltares/Delft-FIAT>`_ models from available global and local data.

This plugin assists the FIAT modeller in:

- Quickly setting up a Delft-FIAT model based on existing hazard maps, global and user-input exposure layers, and global, US national, or user-input vulnerability curves.
- Creating a Social Vulnerability Index (SVI) based on US Census or user-input data.
- Adjusting and updating components of a Delft-FIAT model and their associated parameters in a consistent way.

The HydroMT-FIAT plugin aims to make the FIAT model building process **fast**, **modular**, and **reproducible** 
by configuring the model building process from single *yml* file.

For detailed information on HydroMT itself, you can visit the `core documentation <https://deltares.github.io/hydromt/>`_.

::

   Note: This repository is under development, the documentation is not yet complete!


Overview
=============

**Getting Started**

* :doc:`installation`
* :doc:`examples/index`

**User Guide**

* :doc:`user_guide/user_guide_overview`
* :doc:`data/data_sources`

**Technical documentation**

* :doc:`api/api_index`
* :doc:`changelog`


Contributing
------------

To contribute to HydroMT and the plugin plugin, please follow the 
`HydroMT contribution guidelines <https://deltares.github.io/hydromt/latest/contributing.html>`_.

License
-------

Copyright (c) 2021, Deltares

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public 
License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You can find the full terms of the GNU General Public License at <https://www.gnu.org/licenses/>.

.. toctree::
   :titlesonly:
   :maxdepth: 1
   :hidden:

   installation
   examples/index
   user_guide/user_guide_overview
   data/data_sources
   api/api_index
   changelog
