.. currentmodule:: hydromt_fiat

=============
API reference
=============

.. _api_model:

FIAT model class
================

Initialize
----------

.. autosummary::
   :toctree: ../_generated/

   fiat.FiatModel

Build components
----------------

.. autosummary::
   :toctree: ../_generated/

   fiat.FiatModel.setup_config
   fiat.FiatModel.setup_basemaps
   fiat.FiatModel.setup_hazard
   fiat.FiatModel.setup_exposure_buildings
   fiat.FiatModel.scale_exposure

Attributes
----------

.. autosummary::
   :toctree: ../_generated/

   fiat.FiatModel.region
   fiat.FiatModel.crs
   fiat.FiatModel.res
   fiat.FiatModel.root
   fiat.FiatModel.config
   fiat.FiatModel.staticmaps
   fiat.FiatModel.staticgeoms

High level methods
------------------

.. autosummary::
   :toctree: ../_generated/

   fiat.FiatModel.read
   fiat.FiatModel.write
   fiat.FiatModel.build
   fiat.FiatModel.set_root

General methods
---------------

.. autosummary::
   :toctree: ../_generated/

   fiat.FiatModel.setup_config
   fiat.FiatModel.get_config
   fiat.FiatModel.set_config
   fiat.FiatModel.read_config
   fiat.FiatModel.write_config

   fiat.FiatModel.set_staticmaps
   fiat.FiatModel.read_staticmaps
   fiat.FiatModel.write_staticmaps

   fiat.FiatModel.set_staticgeoms
   fiat.FiatModel.read_staticgeoms
   fiat.FiatModel.write_staticgeoms

   fiat.FiatModel.set_forcing
   fiat.FiatModel.read_forcing
   fiat.FiatModel.write_forcing
