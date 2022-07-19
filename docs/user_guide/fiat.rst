.. _model_components:
.. currentmodule:: hydromt_fiat.fiat

=================================
FIAT model methods and components
=================================

With the HydroMT-FIAT plugin, you can easily work with Delft-FIAT model schematizations.
This plugin helps you preparing or updating  several model components of a Delft-FIAT model 
such as hazard, exposure maps and vulnerability curves.

When building a model from command line a model region_ 
(a bounding box `bbox` or hazard map `grid`); a model setup 
configuration (.ini file) with model methods_ and options and, optionally,
a data_ sources (.yml) file should be prepared. 


The Delft-FIAT model components are available from the HydroMT Command Line and Python Interfaces and 
allow you to configure HydroMT in order to build or update Delft-FIAT model schematizations.
See :ref:`flood damge Delft-FIAT model schematization <fiat_flooding>` for suggested components
and options to use for coastal or riverine applications.

For python users all FIAT attributes and methods are available, see :ref:`api_reference`

.. _methods:

Model setup methods
===================

The following methods are available to build or update Delft-FIAT model schematizations:

.. list-table::
    :widths: 20 55
    :header-rows: 1
    :stub-columns: 1

    * - Method
      - Explanation
    * - :py:func:`~FiatModel.setup_config`
      - Update config with a dictionary
    * - :py:func:`~FiatModel.setup_basemaps`
      - Define the model domain that is used to clip the raster layers.
    * - :py:func:`~FiatModel.setup_hazard`
      - Add a hazard map to the FIAT model schematization.
    * - :py:func:`FiatModel.scale_exposure`
      - Scale the exposure to the forecast year, using the shared socioeconomic pathway (SSP) projections for population and GDP growth.


.. _data: https://deltares.github.io/hydromt/latest/user_guide/data.html
.. _region: https://deltares.github.io/hydromt/latest/user_guide/cli.html#region-options
