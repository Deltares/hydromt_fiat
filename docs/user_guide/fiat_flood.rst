.. _model_components:
.. currentmodule:: hydromt_fiat.fiat

=======================
FIAT model components
=======================

With the hydromt_fiat plugin, you can easily work with Delft-FIAT model schematizations. 
This plugin helps you preparing or updating  several model components of a Delft-FIAT model 
such as hazard, exposure maps and vulnerability curves.

When building a model from command line a model region_ 
(a bounding box `bbox` or hazard map `grid`); a model setup 
configuration (.ini file) with model components_ and options and, optionally, 
a data_ sources (.yml) file should be prepared. 


The Delft-FIAT model components are available from the HydroMT Command Line and Python Interfaces and 
allow you to configure HydroMT in order to build or update Delft-FIAT model schematizations.
See :ref:`flood damge Delft-FIAT model schematization <fiat_flooding>` for suggested components
and options to use for coastal or riverine applications.

For python users all FIAT attributes and methods are available, see :ref:`api_model`

.. _components:

Model components
================

The following components are available to build or update Delft-FIAT model schematizations:

.. autosummary::
   :toctree: ../_generated/
   :nosignatures:

   FiatModel.setup_config
   FiatModel.setup_basemaps
   FiatModel.setup_vulnerability
   FiatModel.setup_exposure_vector
   FiatModel.setup_hazard
   FiatModel.setup_vulnerability

.. _data: https://deltares.github.io/hydromt/latest/user_guide/data.html
.. _region: https://deltares.github.io/hydromt/latest/user_guide/cli.html#region-options