.. _user_guide:
.. currentmodule:: hydromt_fiat.fiat

=======================
User Guide
=======================

With the HydroMT-FIAT plugin, you can easily work with Delft-FIAT model schematizations.
This plugin helps you preparing or updating several model components of a Delft-FIAT model
such as the hazard, exposure and vulnerability data.

When building a model from command line, a model setup configuration file (*.yml* ) and,
optionally, a model region_ (e.g., a bounding box `bbox` or hazard map `grid`) and a
data_catalog_ (*.yml*) file should be prepared.

The Delft-FIAT model methods are available from the HydroMT Command Line and Python Interfaces and
allow you to build or update Delft-FIAT model schematizations.

Built-in data sources are available for the exposure and vulnerability components, see the available
:ref:`data_sources`.

For python users, all FIAT attributes and methods are available, see the :ref:`api_model`.

Exposure
=======================

Vector data
-----------------------

Exposure data can be build from a data_catalog_, a data API key, or by supplying an absolute path
to local data on the user's machine. The `asset_locations`, `occupancy_type`, and `max_potential_damage`
data should be provided as a vector file (e.g. *.shp* or *.gpkg*). The `ground_floor_height` can currently
only be set to a single value (this will be updated soon!). The `damage_types` should be provided as a
list of strings (e.g. ["structure", "content"]). The `length_unit` should be provided as a string (e.g. "meters").
See below how the `setup_exposure_buildings` method can be used to build or update the exposure data::

   [setup_exposure_buildings]
   asset_locations = <Key in the Data Catalog, data API key, or path to local data>
   occupancy_type = <Key in the Data Catalog, data API key, or path to local data>
   damage_types = <List of damage types, e.g. ["structure", "content"]>
   max_potential_damage = <Key in the Data Catalog, data API key, or path to local data>
   ground_floor_height = <For now only a number can be entered here for uniform ground floor heights>
   length_unit = <The unit of the values in the exposure data inputs, e.g. if the ground floor height in meters, "meters">

The following method is used to build or update the **exposure** data:

.. autosummary::
   FiatModel.setup_exposure_buildings

For more information, see the :ref:`exposure_vector`.

Raster data
-----------------------
This option will be implemented at a later stage.


Aggregation Zones
-----------------------
In spatial analysis and urban planning the division of objects into spatial zones, such as land-use or accommodation type, is a pivotal tool to facilitate analysis and/or visualization. The `FIAT toolbox <https://github.com/Deltares/fiat_toolbox>`_ offers simple tools to assign aggregation labels to the exposure.csv file, after calculating damages with `FIAT toolbox <https://github.com/Deltares/delft-fiat>`_. Subsequental, the `FIAT toolbox <https://github.com/Deltares/fiat_toolbox>`_ can be used to automatically calculate metrics over the aggregation areas. The user can add multiple aggregation labels at once by providing vector files for each zone (e.g., *.shp* or *.gpkg*).

To associate the original exposure data with the aggregation zones, the **"join_exposure_aggregation_areas"** function can be utilized. This function seamlessly links each geometry in the original exposure data to its corresponding spatial aggregation zone.
To prepare the data, an aggregation configuration file (*.yml*) must be created with the following information (case-sensitive):

Input yaml file:
   - **new_root**: Path to the output folder
   - **aggregation_area_fn**: Path to the aggregation file
   - **attribute_names**: Name of the zone attribute in your file
   - **label_names**: Desired aggregation label for newly created aggregation zone

In case the user wants to add several aggregation zones at once, multiple aggregation files can be provided in a list. Each variable (file path, attribute name, label name) must follow the same order to assure that attribute and label names are assigned to the correct aggregation file::

   [Example configuration yaml file for two aggregation zone files.]

   Title: "Base_zones and Land_use aggregation zones"
   new_root: "./fiat_model/output/aggregation_zones"
   configuration:
     setup_aggregation_areas:
       aggregation_area_fn:
         - "./agg_zones/base_zone_aggregation.shp"
         - "./agg_zones/land_use_aggregation.shp"
       attribute_names:
         - "ZONE_BASE"
         - "LAND_USE"
       label_names:
         - "Base Zone"
         - "Land Use"

After loading the configuration file (*.yml*) and executing the **FIAT Hydro MT** model builder, the user receives a file (*.csv*) with the original exposure data and an additional column with the aggregation label(s) as output. The `FIAT toolbox <https://github.com/Deltares/delft-fiat>`_ will automatically prepend "*Aggregation Label*" to the prior specified aggregation label, therefore the aggregation labels can be identified as such.

   Aggregation Label: {label_name}

*Note: It may occur that polygons overlap in the aggregation vector files. In this case the information for the affected Object ID will be merged and both aggregation zones will be assigned to the object.* ::

   Object ID   Zone

   1           Base Zone 1
   2           Land Use 1, Land Use 3    >  two zones (polygons) in the land-use aggregation file overlap and object
                                            falls into both zones
   3           Land Use 2



Vulnerability
=======================
Vulnerability data can be build from a data_catalog_ or by supplying an absolute path
to local data on the user's machine. The `vulnerability_fn` and `vulnerability_identifiers_and_linking_fn`
data should be provided as a csv file (*.csv*). The `functions_mean` and `functions_max` parameters
can be used when an aereal calculation is done (i.e., taking the hazard value over the whole area of the
building footprint or over the whole length of the linestring). The user can use one of the parameters as
a default by setting it to "default". If required, the user can provide the names of the damage functions
as a list to `functions_mean` or `functions_max` to respectively use the mean or max hazard value for all
assets that use that damage function. The `damage_types` should be provided as a
list of strings (e.g. ["structure", "content"]). The `unit` should be provided as a string (e.g. "meters").
The `step_size` should be provided as a float (e.g. 0.01).
See below how the `setup_vulnerability` method can be used to build or update the exposure data::

   [setup_vulnerability]
   vulnerability_fn = <Key in the Data Catalog or absolute path to local data>
   vulnerability_identifiers_and_linking_fn = <Key in the Data Catalog or absolute path to local data>
   functions_mean = <List of functions to use the mean water depth or level for, or "default" when using the mean should be used for all damage functions>
   functions_max = <List of functions to use the mean water depth or level for, or "default" when using the mean should be used for all damage functions>
   unit = <The unit of the values in the vulnerability data inputs, e.g. if the water depth is in meters, "m">
   step_size = <The step size Delft-FIAT should use to interpolate the values in the damage functions, this is set to 0.01 by default>

The following methods can be used to build or update the **vulnerability** data:

.. autosummary::
   FiatModel.setup_vulnerability
   FiatModel.setup_vulnerability_from_csv

For more information, see the :ref:`vulnerability`.

Hazard
=======================
The following methods can be used to build or update the **hazard** data:

.. autosummary::
   FiatModel.setup_hazard

For more information, see the :ref:`hazard`.

Social Vulnerability Index
===========================
The following methods can be used to build or update the **Social Vulnerability Index** data:

.. autosummary::
   FiatModel.setup_social_vulnerability_index

For more information, see the :ref:`svi`.

Output and run settings
========================
The following methods are available to set up the **output and run settings** for Delft-FIAT:

.. autosummary::
   FiatModel.setup_global_settings
   FiatModel.setup_output


.. _data_catalog: https://deltares.github.io/hydromt/latest/user_guide/data_prepare_cat.html
.. _region: https://deltares.github.io/hydromt/latest/user_guide/cli.html#region-options

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Modules

   exposure_vector
   vulnerability
   hazard
   social_vulnerability_index
