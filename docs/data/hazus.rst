.. _hazus:

===============================================
HAZUS flood depth-damage functions
===============================================

Users of **HydroMT-FIAT** can directly and easily make use of the depth-damage 
functions and repair values from `HAZUS 
<https://www.fema.gov/flood-maps/products-tools/hazus>`_. Hazus is a US-based 
program and the depth-damage functions are based on US data. The functions and 
values can be used only together with the `hydromt_fiat_catalog_USA.yml` and 
by providing the following values in the configuration file::

    [setup_vulnerability]
    vulnerability_fn = "default_vulnerability_curves"
    vulnerability_identifiers_and_linking_fn = "default_hazus_iwr_linking"
    unit = "ft"

    [setup_exposure_vector]
    max_potential_damage = "hazus_max_potential_damages"
    unit = "m"


The HAZUS flood depth-damage functions and replacement values are processed into an easy-to-use format 
for HydroMT-FIAT and stored in the ``hydromt_fiat/data`` folder.

