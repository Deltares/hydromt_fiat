.. _user_guide_data_hazard:

===========
Hazard data
===========

Hazard data represents the spatial distribution and intensity of a flood event.
In the context of Delft-FIAT, this is typically a **water depth map** that describes
how deep the flooding is at each location in the study area.

What is hazard data?
--------------------

A hazard map is a gridded (raster) dataset where each cell contains the flood intensity
value — usually **water depth in meters**. HydroMT-FIAT supports both single-event
maps and multiple maps for risk analysis (with associated return periods).

.. code-block:: text

    ┌─────────────────────────────────────┐
    │  Flood Depth Map (meters)           │
    │                                     │
    │  0.0  0.1  0.3  0.5  0.2  0.0      │
    │  0.0  0.2  0.8  1.2  0.6  0.1      │
    │  0.1  0.5  1.5  2.0  1.0  0.3      │
    │  0.0  0.3  0.9  1.4  0.7  0.2      │
    │  0.0  0.1  0.4  0.6  0.3  0.0      │
    │                                     │
    └─────────────────────────────────────┘

Expected format
---------------

HydroMT-FIAT expects hazard data as **raster files** (georeferenced grids):

- **Supported formats:** GeoTIFF (``.tif``), NetCDF (``.nc``), or any GDAL-readable
  raster format
- **Dimensions:** 2D spatial grid with x and y coordinates
- **Values:** Flood intensity values (typically water depth in meters)
- **CRS:** Any projected or geographic coordinate reference system
- **NoData:** Areas without flooding should have a NoData value or 0

Key properties
~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Property
     - Description
   * - Spatial resolution
     - Grid cell size (e.g., 5m, 10m, 100m). Finer resolution captures more detail
       but increases computation time.
   * - CRS
     - Coordinate reference system. Should match or be transformable to the exposure
       data CRS.
   * - Hazard type
     - Type of hazard intensity (e.g., ``water depth``, ``flood level``). Determines
       how Delft-FIAT interprets the values.
   * - Unit
     - Physical unit of the hazard values (default: meters).

Event analysis vs. risk analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

HydroMT-FIAT supports two analysis modes:

**Event analysis** (single map):
    A single flood map representing one specific event. Produces damage estimates for
    that particular scenario.

**Risk analysis** (multiple maps with return periods):
    Multiple flood maps, each associated with a return period (e.g., 10-year, 100-year,
    1000-year). Delft-FIAT integrates the damage over return periods to compute
    Expected Annual Damage (EAD).

.. code-block:: text

    Event analysis:         Risk analysis:
    ┌────────────┐          ┌────────────┐  RP = 10 yr
    │ Flood map  │          │ Flood map  │
    └────────────┘          ├────────────┤  RP = 100 yr
                            │ Flood map  │
                            ├────────────┤  RP = 1000 yr
                            │ Flood map  │
                            └────────────┘

Where to get hazard data
------------------------

Common sources for flood hazard maps:

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Source
     - Description
     - Reference
   * - SFINCS
     - Fast compound flood model (wind, rain, tide, surge)
     - `Leijnse et al. (2021) <https://doi.org/10.1016/j.coastaleng.2020.103796>`_
   * - Wflow
     - Hydrological model for inland/fluvial flooding
     - `van Verseveld et al. (2022) <https://doi.org/10.5194/gmd-2022-182>`_
   * - JRC Global Flood Maps
     - Global river flood maps at various return periods
     - `Dottori et al. (2021) <https://doi.org/10.1029/2021EF002285>`_
   * - Aqueduct Floods
     - Global flood hazard maps (WRI)
     - `Ward et al. (2020) <https://doi.org/10.1038/s41467-019-14108-0>`_
   * - Local authorities
     - Regional/national flood maps from water management agencies
     -

.. tip::

    HydroMT-FIAT includes a small test flood map. Use ``fetch_data("test-build-data")``
    to download it.

Data catalog entry
------------------

Hazard data is defined in the data catalog with ``data_type: RasterDataset``:

.. code-block:: yaml

    flood_event:
      data_type: RasterDataset
      uri: hazard/flood_map.tif
      driver:
        name: rasterio
        filesystem: local
        options:
          chunks:
            x: 1500
            y: 1500
      metadata:
        category: hazard
        crs: 28992
        source_version: 1.0

For **risk analysis** with multiple return periods, define separate entries for each
return period map:

.. code-block:: yaml

    flood_rp010:
      data_type: RasterDataset
      uri: hazard/flood_rp010.tif
      driver:
        name: rasterio
      metadata:
        category: hazard
        crs: 28992

    flood_rp100:
      data_type: RasterDataset
      uri: hazard/flood_rp100.tif
      driver:
        name: rasterio
      metadata:
        category: hazard
        crs: 28992

Usage in model building
-----------------------

Hazard data is set up using the
:py:meth:`~hydromt_fiat.components.HazardComponent.setup` method:

.. code-block:: python

    # Single event analysis
    model.hazard.setup(
        hazard_fnames="flood_event",
        hazard_type="water depth",
    )

    # Risk analysis (multiple return periods)
    model.hazard.setup(
        hazard_fnames=["flood_rp010", "flood_rp100", "flood_rp1000"],
        hazard_type="water depth",
        risk=True,
        return_periods=[10, 100, 1000],
    )

Parameters:

- ``hazard_fnames``: Data catalog entry name(s) or file path(s)
- ``hazard_type``: Type of hazard (e.g., ``"water depth"``)
- ``risk``: Set to ``True`` for risk analysis
- ``return_periods``: List of return periods (must match number of hazard files)
- ``unit``: Unit of hazard values (default: ``"m"``)
