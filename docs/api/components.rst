.. currentmodule:: hydromt_fiat.components

.. raw:: html

    <style>
        /* Default (light mode) */
        html[data-theme="light"] h2 {
            border-bottom: 1px solid #000;
        }
        /* Dark mode */
        html[data-theme="dark"] h2 {
            border-bottom: 1px solid #d1d5db;
        }
    </style>

.. _api_components:

Components
==========
These are the FIATModel components.


Initialize
----------

.. autosummary::
    :toctree: ../_generated

    ConfigComponent
    VulnerabilityComponent
    HazardComponent
    ExposureGeomsComponent
    ExposureGridComponent

ConfigComponent
---------------

.. autosummary::
    :toctree: ../_generated

    ConfigComponent.data
    ConfigComponent.read
    ConfigComponent.write
    ConfigComponent.clear

VulnerabilityComponent
----------------------

.. autosummary::
    :toctree: ../_generated

    VulnerabilityComponent.data
    VulnerabilityComponent.read
    VulnerabilityComponent.write
    VulnerabilityComponent.clear
    VulnerabilityComponent.setup

HazardComponent
---------------

.. autosummary::
    :toctree: ../_generated

    HazardComponent.data
    HazardComponent.read
    HazardComponent.write
    HazardComponent.clear
    HazardComponent.clip
    HazardComponent.reproject
    HazardComponent.setup

ExposureGeomsComponent
----------------------

.. autosummary::
    :toctree: ../_generated

    ExposureGeomsComponent.data
    ExposureGeomsComponent.read
    ExposureGeomsComponent.write
    ExposureGeomsComponent.clear
    ExposureGeomsComponent.clip
    ExposureGeomsComponent.reproject
    ExposureGeomsComponent.setup
    ExposureGeomsComponent.setup_max_damage
    ExposureGeomsComponent.update_column

ExposureGridComponent
---------------------

.. autosummary::
    :toctree: ../_generated

    ExposureGridComponent.data
    ExposureGridComponent.read
    ExposureGridComponent.write
    ExposureGridComponent.clear
    ExposureGridComponent.clip
    ExposureGridComponent.reproject
    ExposureGridComponent.setup
