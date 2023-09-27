.. _nsi:

==================================
National Structure Inventory (USA)
==================================

For projects in the United States, users of **HydroMT-FIAT** can directly and easily make use 
of the `National Structure Inventory <https://www.hec.usace.army.mil/confluence/nsi>`_ (NSI). The 
user can access the data through providing 'NSI' in the configuration file as such::

    [setup_exposure_vector]
    asset_locations = "NSI"
    occupancy_type = "NSI"
    max_potential_damage = "NSI"

The following attributes for Delft-FIAT (left-hand side) will be filled with data from the 
corresponding NSI fields (right-hand side)::

    "Object ID": "fd_id",
    "Object Name": "fd_id",
    "Primary Object Type": "st_damcat",
    "Secondary Object Type": "occtype",
    "Max Potential Damage: Structure": "val_struct",
    "Max Potential Damage: Content": "val_cont",
    "Ground Elevation": "ground_el",
    "X Coordinate": "x",
    "Y Coordinate": "y",
    "Aggregation Label: Census Block": "cbfips"

HydroMT-FIAT obtains the NSI data of the area of interest through the `NSI API 
<https://www.hec.usace.army.mil/confluence/nsi/technicalreferences/latest/api-reference-guide>`_.

For more information about this data we refer to their online `Technical Documentation 
<https://www.hec.usace.army.mil/confluence/nsi/technicalreferences/latest/technical-documentation>`_.
