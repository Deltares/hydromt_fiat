.. _user_guide_model_components:

================
Model components
================

An overview of all the FIATModel components are presented in the table below:

.. currentmodule:: hydromt_fiat.components

.. list-table::
   :widths: 30 55 15
   :header-rows: 1

   * - Component
     - Information
     - Format
   * - :class:`ConfigComponent`
     - Handles the Delft-FIAT model configurations
     - TOML
   * - :class:`VulnerabilityComponent`
     - Handles the tabular vulnerability data, i.e. damage curves
     - CSV
   * - :class:`HazardComponent`
     - Handles the hazard data
     - netCDF
   * - :class:`ExposureGeomsComponent`
     - Handles the exposure data that is in a vector format
     - FlatGeobuf
   * - :class:`ExposureGeomsComponent`
     - Handles the exposure data that is in a raster format
     - netCDF

All of these components need (raw) input data when trying to set up data for Delft-FIAT.
Most common is defining the data in a HydroMT `data catalog <Data_Catalog_>`_ and use
the created entry in the data catalog as input.

.. _Data_Catalog: https://deltares.github.io/hydromt/stable/guides/advanced_user/data_prepare_cat.html
