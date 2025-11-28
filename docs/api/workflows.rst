.. currentmodule:: hydromt_fiat

.. raw:: html

    <style>
        h2 {
            border-bottom: 1px solid #000;
        }
    </style>

.. _api_workflows:

Workflow functions
==================

The underlying workflow methods of the components.

Vulnerability
-------------

.. autosummary::
    :toctree: ../_generated

    workflows.vulnerability_setup

Hazard
------

.. autosummary::
    :toctree: ../_generated

    workflows.hazard_setup

Exposure (geometry)
-------------------

.. autosummary::
    :toctree: ../_generated

    workflows.exposure_geoms_setup
    workflows.exposure_geoms_link_vulnerability
    workflows.max_monetary_damage
    workflows.exposure_geoms_add_columns

Exposure (grid)
---------------

.. autosummary::
    :toctree: ../_generated

    workflows.exposure_grid_setup
