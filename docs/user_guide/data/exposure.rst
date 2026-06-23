.. _user_guide_data_exposure:

=============
Exposure data
=============

Exposure data describes the assets at risk from flooding. These are typically
**building footprints** or **asset locations** with associated attributes such as
occupancy type, value, and elevation.

What is exposure data?
----------------------

In flood damage assessment, exposure data answers the question: *"What is at risk?"*
It provides the spatial location and characteristics of assets (buildings,
infrastructure, etc.) that can be damaged by flooding.

Each asset needs at minimum:

- A **geometry** (location/footprint)
- An **object type** (e.g., residential, commercial) to link to vulnerability curves
- A **maximum damage value** to convert damage fractions to monetary losses

Expected format
---------------

HydroMT-FIAT expects exposure data as **vector files** (geospatial features):

- **Supported formats:** GeoPackage (``.gpkg``), FlatGeobuf (``.fgb``), GeoJSON,
  ESRI Shapefile, or any format readable by pyogrio/GDAL
- **Geometry types:** Point, Polygon, or MultiPolygon
- **CRS:** Any coordinate reference system (will be reprojected to match model CRS)

Required attributes
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 20 55
   :header-rows: 1

   * - Column
     - Type
     - Description
   * - ``geometry``
     - Geometry
     - Spatial feature (point or polygon). Auto-included in GeoDataFrame.
   * - Object type column
     - String
     - A column identifying the occupancy/building type (e.g., ``residential``,
       ``commercial``). The column name is specified during setup.

Optional attributes (added during model building)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These columns are typically **added by HydroMT-FIAT** during the model building
process, rather than being present in the raw input data:

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Column
     - Type
     - Description
   * - ``object_id``
     - Integer
     - Unique identifier per feature (auto-generated if missing)
   * - ``object_type``
     - String
     - Standardized object type (after linking table mapping)
   * - ``fn_damage_structure``
     - String
     - Name of the structure vulnerability curve
   * - ``fn_damage_content``
     - String
     - Name of the content vulnerability curve
   * - ``max_damage_structure``
     - Float
     - Maximum potential structural damage (monetary)
   * - ``max_damage_content``
     - Float
     - Maximum potential content damage (monetary)
   * - ``elevatio``
     - Float
     - Ground or building floor elevation (meters)

Linking table
~~~~~~~~~~~~~

A **linking table** maps raw object/building types from your exposure data to
standardized types used by HydroMT-FIAT. This is a CSV file with columns:

.. code-block:: text

    source_type,object_type
    apartments,residential
    house,residential
    retail,commercial
    warehouse,industrial
    school,commercial
    unknown,residential

This allows flexible mapping from diverse data sources (e.g., OpenStreetMap ``building``
tags) to a standardized classification.

Where to get exposure data
--------------------------

Common sources for building/asset data:

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Source
     - Description
     - Reference
   * - OpenStreetMap (OSM)
     - Crowd-sourced building footprints worldwide
     - `openstreetmap.org <https://www.openstreetmap.org/>`_
   * - Microsoft Building Footprints
     - AI-derived building footprints (global coverage)
     - `GitHub <https://github.com/microsoft/GlobalMLBuildingFootprints>`_
   * - Google Open Buildings
     - ML-derived footprints for Africa, South/Southeast Asia, Latin America
     - `sites.research.google <https://sites.research.google/open-buildings/>`_
   * - National registers (BAG, Kadaster)
     - Official building registries (country-specific)
     -
   * - Custom surveys
     - Local asset inventories from fieldwork or local authorities
     -

.. tip::

    HydroMT-FIAT can directly query OpenStreetMap buildings using the built-in
    ``osm_buildings`` data source (requires network access). Use
    ``fetch_data("global-data")`` for offline test data.

Data catalog entry
------------------

Exposure data is defined in the data catalog with ``data_type: GeoDataFrame``:

.. code-block:: yaml

    buildings:
      data_type: GeoDataFrame
      uri: exposure/buildings.fgb
      driver:
        name: pyogrio
        filesystem: local
      metadata:
        category: exposure
        crs: 4326
        source_version: 1.0

    # Optional: linking table for type mapping
    buildings_link:
      data_type: DataFrame
      uri: exposure/buildings_link.csv
      driver:
        name: pandas
        filesystem: local
        options:
          index_col: 0
      metadata:
        category: exposure

    # Optional: maximum damage values per type
    damage_values:
      data_type: DataFrame
      uri: exposure/max_damage.csv
      driver:
        name: pandas
        filesystem: local
        options:
          index_col: 0
      metadata:
        category: exposure

Usage in model building
-----------------------

Exposure data is set up using the
:py:meth:`~hydromt_fiat.components.ExposureGeomsComponent.setup` method and related
methods:

.. code-block:: python

    # Step 1: Load exposure geometries
    model.exposure_geoms.setup(
        exposure_fname="buildings",
        exposure_object_type_column="building",  # column in your data
        exposure_link_fname="buildings_link",     # linking table
        exposure_object_type_fill="unknown",      # default for missing types
    )

    # Step 2: Link to vulnerability curves
    model.exposure_geoms.setup_link_vulnerability(
        exposure_name="buildings",
        impact_type="damage",
    )

    # Step 3: Add maximum damage values
    model.exposure_geoms.setup_max_damage(
        exposure_name="buildings",
        impact_type="damage",
        exposure_cost_table_fname="damage_values",
        country="World",
    )

    # Step 4 (optional): Set elevation
    model.exposure_geoms.update_column(
        exposure_name="buildings",
        columns=["elevatio"],
        values=[0],
    )

.. important::

    The **vulnerability component must be set up before** linking exposure to
    vulnerability curves. HydroMT-FIAT uses the vulnerability data to validate
    that the referenced curves exist.

.. warning::

    Features in the exposure data that cannot be mapped through the linking table
    are **silently dropped** (with a warning logged). Ensure your linking table
    covers all object types present in the data, or use ``exposure_object_type_fill``
    to assign a default type to unmapped features.
