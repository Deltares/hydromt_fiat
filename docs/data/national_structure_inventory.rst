.. _nsi:

==================================
National Structure Inventory (USA)
==================================

For projects in the United States, users of **HydroMT-FIAT** can directly and easily make use
of the `National Structure Inventory <https://www.hec.usace.army.mil/confluence/nsi>`_ (NSI). The
user can access the data through providing 'NSI' in the configuration file as such::

    [setup_exposure_buildings]
    asset_locations = "NSI"
    occupancy_type = "NSI"
    max_potential_damage = "NSI"

The following attributes for Delft-FIAT (left-hand side) will be filled with data from the
corresponding NSI fields (right-hand side)::

    "object_id": "fd_id",
    "object_name": "fd_id",
    "primary_object_type": "st_damcat",
    "secondary_object_type": "occtype",
    "max_damages_structure": "val_struct",
    "max_damages_content": "val_cont",
    "ground_elevtn": "ground_el",
    "X Coordinate": "x",
    "Y Coordinate": "y",
    "Aggregation Label: Census Block": "cbfips"

HydroMT-FIAT obtains the NSI data of the area of interest through the `NSI API
<https://www.hec.usace.army.mil/confluence/nsi/technicalreferences/latest/api-reference-guide>`_.

For more information about this data we refer to their online `Technical Documentation
<https://www.hec.usace.army.mil/confluence/nsi/technicalreferences/latest/technical-documentation>`_.
