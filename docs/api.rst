.. currentmodule:: hydromt_fiat

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

.. _setup_methods:

Setup methods
-------------

.. autosummary::
    :toctree: _generated

    FIATModel.setup_config
    FIATModel.setup_region
    FIATModel.setup_hazard
    FIATModel.setup_vulnerability

.. _model_io:

I/O methods
-----------

.. autosummary::
    :toctree: _generated

    FIATModel.read
    FIATModel.write

.. _model_attributes:

Attributes
----------

.. autosummary::
    :toctree: _generated

    FIATModel.config
    FIATModel.region
    FIATModel.hazard_grid
    FIATModel.vulnerability_data

Workflow functions
==================

The underlying workflow methods of the FIATModel.

.. autosummary::
    :toctree: _generated

    workflows.vulnerability_curves
