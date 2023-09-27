.. _osm:

===============================================
OpenStreetMap Building Footprints and Land Use
===============================================

Users of **HydroMT-FIAT** can directly and easily make use of the `OpenStreetMap <https://www.openstreetmap.org/about>`_ 
(OSM) initiative. The user can access the data through providing 'OSM' in the configuration file as such::

    [setup_exposure_vector]
    asset_locations = "OSM"
    occupancy_type = "OSM"

HydroMT-FIAT obtains the OSM data of the area of interest through the OSMnx package [1].


[1] Boeing, G. 2017. "`OSMnx: New Methods for Acquiring, Constructing, Analyzing, and Visualizing Complex 
Street Networks. <https://geoffboeing.com/publications/osmnx-complex-street-networks/>`_" Computers, Environment 
and Urban Systems 65, 126-139.