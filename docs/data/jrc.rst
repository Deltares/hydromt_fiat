.. _jrc:

===============================================
JRC Global flood depth-damage functions
===============================================

Users of **HydroMT-FIAT** can directly and easily make use of the `JRC Global flood depth-damage functions and 
replacement values <https://publications.jrc.ec.europa.eu/repository/handle/JRC105688>`_ [1]. The functions and 
values can be used only together with the `hydromt_fiat_catalog_global.yml` and 
by providing the following values in the configuration file::

    [setup_vulnerability]
    vulnerability_fn = "jrc_vulnerability_curves"
    vulnerability_identifiers_and_linking_fn = "jrc_vulnerability_curves_linking"
    unit = "m"

    [setup_exposure_buildings]
    max_potential_damage = "jrc_damage_values"
    unit = "m"


The JRC Global flood depth-damage functions and replacement values are processed into an easy-to-use format 
for HydroMT-FIAT and stored in the ``hydromt_fiat/data`` folder.


[1] Huizinga, J., De Moel, H. and Szewczyk, W., Global flood depth-damage functions: Methodology 
and the database with guidelines, EUR 28552 EN, Publications Office of the European Union, Luxembourg, 
2017, ISBN 978-92-79-67781-6, doi:10.2760/16510, JRC105688.