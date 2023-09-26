.. _model_components:
.. currentmodule:: hydromt_fiat.fiat

=======================
FIAT model components
=======================

With the hydromt_fiat plugin, you can easily work with Delft-FIAT model schematizations. 
This plugin helps you preparing or updating several model components of a Delft-FIAT model 
such as the hazard, exposure and vulnerability data.

When building a model from command line, a model setup 
configuration (.yml file) with model components_ and, optionally,
a model region_ (a bounding box `bbox` or hazard map `grid`) and
a data_catalog_ (.yml) file should be prepared. 


The Delft-FIAT model components are available from the HydroMT Command Line and Python Interfaces and 
allow you to configure HydroMT in order to build or update Delft-FIAT model schematizations.

For python users all FIAT attributes and methods are available, see :ref:`api_model`

.. _components:

Model components
================

The following components are available to build or update Delft-FIAT model schematizations:

.. autosummary::
   :toctree: ../_generated/
   :nosignatures:

   FiatModel.setup_global_settings
   FiatModel.setup_output
   FiatModel.setup_basemaps
   FiatModel.setup_vulnerability
   FiatModel.setup_vulnerability_from_csv
   FiatModel.setup_exposure_vector
   FiatModel.setup_hazard
   FiatModel.setup_social_vulnerability_index

.. _data_catalog: https://deltares.github.io/hydromt/latest/user_guide/data_prepare_cat.html
.. _region: https://deltares.github.io/hydromt/latest/user_guide/cli.html#region-options
