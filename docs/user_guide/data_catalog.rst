.. currentmodule:: hydromt_fiat.components

.. _user_guide_data_catalog:

============
Data Catalog
============

The data catalog is the way of providing a HydroMT model class with raw data to chose
from when setting up the data for a model. In case of HydroMT-FIAT, this is done for
the data mentioned in the :ref:`data <user_guide_data_index>` section. The data catalog for
HydroMT-FIAT therefore caters to vector, raster and tabular data. This section will
show a brief overview of a data catalog entry for each of them.

.. important::

    The format of the data catalog is `YAML <https://yaml.org/>`_.

.. warning::

    Not all data catalog functionality is specified here, for more information see
    the `data catalog <https://deltares.github.io/hydromt/stable/user_guide/data_catalog/data_overview.html>`_ information in HydroMT-core.

Meta
----
It is good practice to start each data catalog with the *meta* section.
This section is not necessary however as data is automatically searched for relative
to the data catalog's location.

.. code-block:: yaml

    meta:
      roots:
        - < root-to-data-location-1 >
        - < root-to-data-location-2 >
      version: < version >
      name: < name >

Vector
------
This section will effectively entail the exposure geometry data. The driver is always
defined as **pyogrio** and the data_type is always set to **GeoDataFrame**.

Example data catalog entry:

.. code-block:: yaml

    < your-dataset-name >:
      data_type: GeoDataFrame
      uri: < path-to-dataset >
      driver:
        name: pyogrio
        filesystem: local
      rename: # Optional
        < columns-name >: < new-column-name >
      unit_add: # Optional
        < columns-name >: < value >
      unit_mult: # Optional
        < columns-name >: < value >
      metadata: # Optional, but good practice
        category: < data-category >
        crs: 4326 # Whatever the dataset is in
        source_version: 1.0

Explanation of optional vector data entry options:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - rename
     - Rename a column header of the attribute table
   * - unit_add
     - Add a set value to the values in a numerical column
   * - unit_multi
     - Multiply the values of a numerical column with a set value

This data entry is mainly called upon by:

* :py:meth:`ExposureGeomsComponent.setup`

Raster
------
This section will cover the data that is needed for setup up the hazard data and the
gridded exposure data. The data type of a raster data entry is always set to
**rasterdataset**. In contrast to the vector data entry, two drivers are applicable
in the case of raster data. These are listed in the small table down below:

.. list-table::
   :align: center
   :width: 60%
   :widths: 15 40
   :header-rows: 1

   * - Driver name
     - Data type
   * - rasterio
     - Spatially referenced gridded data readable by GDAL (e.g. .tif)
   * - raster_xarray
     - Spatially referenced netCDF data (.nc) and zarr archives (.zarr)

Example data catalog entry:

.. code-block:: yaml

    < your-dataset-name >:
      data_type: RasterDataset
      uri: < path-to-dataset >
      driver:
        name: < driver-name >
        filesystem: local
        options:
          chunk: # Not necessary, but very handy for large datasets
            < x-dim >: < value > # e.g. lon: 1000
            < y-dim >: < value >
      rename: # Optional
        < columns-name >: < new-column-name >
      unit_add: # Optional
        < columns-name >: < value >
      unit_mult: # Optional
        < columns-name >: < value >
      metadata: # Optional, but good practice
        category: < data-category >
        crs: 4326 # Whatever the dataset is in
        source_version: 1.0

Explanation of optional raster data entry options:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - chunk (driver options)
     - Set the chunking per dimension specific
   * - rename
     - Rename a variable (layer or band) in the dataset
   * - unit_add
     - Add a set value to the numerical variable
   * - unit_multi
     - Multiply a numerical variable with a set value

This data entry is mainly called upon by:

* :py:meth:`HazardComponent.setup`
* :py:meth:`ExposureGeomsComponent.setup`

Tabular
-------
Tabular data is used in most places throughout HydroMT-FIAT either as direct concrete
input for the vulnerability data or as linking tables in other different places.
The data type of tabular data is always defined as **DataFrame** and the driver is
always set to **pandas**.

Example data catalog entry:

.. code-block:: yaml

    < your-dataset-name >:
      data_type: DataFrame
      uri: < path-to-dataset >
      driver:
        name: pandas
        filesystem: local
        options:
          header: null  # null translates to None in Python -> no header
          index_col: 0 # Chose the first column as index
          parse_dates: false # Whether or not to parse datetime entries
      rename: # Optional
        < columns-name >: < new-column-name >
      unit_add: # Optional
        < columns-name >: < value >
      unit_mult: # Optional
        < columns-name >: < value >
      metadata:
        category: < data-category >
        source_version: 1.0

Explanation of optional tabular data entry options:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - header (driver options)
     - Whether or not to set a row as the column headers and which row
   * - index_col (driver options)
     - Which column to use as the index for the rows
   * - rename
     - Rename a column header of the attribute table
   * - unit_add
     - Add a set value to the values in a numerical column
   * - unit_multi
     - Multiply the values of a numerical column with a set value

This data entry is mainly called upon by:

* :py:meth:`VulnerabilityComponent.setup`
* :py:meth:`ExposureGeomsComponent.setup`
* :py:meth:`ExposureGeomsComponent.setup_link_vulnerability`
* :py:meth:`ExposureGeomsComponent.setup_max_damage`
* :py:meth:`ExposureGridComponent.setup`
