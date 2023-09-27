.. currentmodule:: hydromt_fiat

.. _api_model:

=============
API reference
=============

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
   fiat.FiatModel.setup_vulnerability
   fiat.FiatModel.setup_exposure_vector
   fiat.FiatModel.setup_hazard
   fiat.FiatModel.setup_social_vulnerability_index

Attributes
----------

.. autosummary::
   :toctree: ../_generated/

   fiat.FiatModel.region
   fiat.FiatModel.crs
   fiat.FiatModel.res
   fiat.FiatModel.root
   fiat.FiatModel.config
   fiat.FiatModel.maps
   fiat.FiatModel.geoms

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

   fiat.FiatModel.set_maps
   fiat.FiatModel.read_maps
   fiat.FiatModel.write_maps

   fiat.FiatModel.set_geoms
   fiat.FiatModel.read_geoms
   fiat.FiatModel.write_geoms