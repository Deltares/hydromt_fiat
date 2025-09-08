.. currentmodule:: hydromt_fiat

.. raw:: html

    <style>
        h2 {
            border-bottom: 1px solid #000;
        }
    </style>

.. _api_reference:

#############
API reference
#############

.. _api_model:

FIAT model class
================

All FIATModel related operations and attributes.

Initialize
----------

.. autosummary::
    :toctree: _generated
    :template: autosummary/class.rst

    FIATModel

.. _model_attributes:

Attributes
----------

.. autosummary::
    :toctree: _generated

    FIATModel.config
    FIATModel.region
    FIATModel.vulnerability
    FIATModel.hazard
    FIATModel.exposure_geoms
    FIATModel.exposure_grid

.. _model_io:

I/O methods
-----------

.. autosummary::
    :toctree: _generated

    FIATModel.read
    FIATModel.write

.. _model_setup_methods:

Model setup methods
-------------------

.. autosummary::
    :toctree: _generated

    FIATModel.setup_config
    FIATModel.setup_region

.. currentmodule:: hydromt_fiat.components

.. _component_setup_methods:

Component setup methods
-----------------------

.. autosummary::
    :toctree: _generated

    VulnerabilityComponent.setup
    HazardComponent.setup
    ExposureGeomsComponent.setup
    ExposureGeomsComponent.setup_max_damage
    ExposureGeomsComponent.update_column
    ExposureGridComponent.setup

.. currentmodule:: hydromt_fiat

.. _workflow_functions:

Workflow functions
==================

The underlying workflow methods of the FIATModel.

.. autosummary::
    :toctree: _generated

    workflows.vulnerability_curves
    workflows.hazard_grid
    workflows.exposure_setup
    workflows.exposure_vulnerability_link
    workflows.exposure_add_columns
    workflows.max_monetary_damage
    workflows.exposure_grid_setup

.. _drivers:

Drivers
=======

Added drivers specifically for HydroMT-FIAT

.. autosummary::
    :toctree: _generated
    :template: autosummary/class_noinherit.rst

    drivers.OSMDriver

OSMDriver methods
-----------------

.. autosummary::
    :toctree: _generated

    drivers.OSMDriver.get_osm_data
    drivers.OSMDriver.read
    drivers.OSMDriver.write
