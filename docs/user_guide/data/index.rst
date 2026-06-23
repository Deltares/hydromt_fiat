.. _user_guide_data_index:

====
Data
====

HydroMT-FIAT requires three core types of input data to build a Delft-FIAT model:

.. grid:: 3
    :gutter: 1

    .. grid-item-card::
        :text-align: center
        :link: user_guide_data_vulnerability
        :link-type: ref

        :octicon:`graph;5em`
        +++
        Vulnerability

    .. grid-item-card::
        :text-align: center
        :link: user_guide_data_hazard
        :link-type: ref

        :octicon:`alert;5em`
        +++
        Hazard

    .. grid-item-card::
        :text-align: center
        :link: user_guide_data_exposure
        :link-type: ref

        :octicon:`location;5em`
        +++
        Exposure

Each data type plays a specific role in the flood damage assessment:

- **Vulnerability** data defines the relationship between hazard intensity (e.g., water
  depth) and damage as a fraction of maximum potential loss. This is expressed through
  depth-damage curves.
- **Hazard** data represents the spatial distribution of the flood event, typically as
  a raster grid with water depth values.
- **Exposure** data describes the assets at risk (e.g., buildings), including their
  location, type, and value.

These data are combined by Delft-FIAT to compute flood damage for a given scenario.

.. note::

    All data is provided to HydroMT-FIAT through a
    :ref:`data catalog <user_guide_data_catalog>`. See the
    :ref:`data catalog <user_guide_data_catalog>` section for details on how to
    define data sources.

.. toctree::
   :caption: Table of Contents
   :maxdepth: 2
   :hidden:

   vulnerability.rst
   hazard.rst
   exposure.rst
