.. _model_user_guide:

==================
Model & components
==================

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
   * - :class:`RegionComponent`
     - Contains the region polygon defining the model extent
     - GeoJSON
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
