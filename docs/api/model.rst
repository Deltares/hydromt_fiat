.. currentmodule:: hydromt_fiat

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

.. _api_model:

FIATModel
=========

All FIATModel related operations and attributes.

Initialize
----------

.. autosummary::
    :toctree: ../_generated
    :template: autosummary/class.rst

    FIATModel

.. _api_model_attributes:

Attributes
----------

.. autosummary::
    :toctree: ../_generated

    FIATModel.config
    FIATModel.region
    FIATModel.vulnerability
    FIATModel.hazard
    FIATModel.exposure_geoms
    FIATModel.exposure_grid

.. _api_model_io:

I/O methods
-----------

.. autosummary::
    :toctree: ../_generated

    FIATModel.read
    FIATModel.write

.. _api_model_setup_methods:

Model setup methods
-------------------

.. autosummary::
    :toctree: ../_generated

    FIATModel.setup_config
    FIATModel.setup_region

.. _api_model_mutating_methods:

Model mutating methods
----------------------

.. autosummary::
    :toctree: ../_generated

    FIATModel.clear
    FIATModel.clip
    FIATModel.reproject
