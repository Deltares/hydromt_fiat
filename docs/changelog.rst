What's new
==========
All notable changes to this project will be documented in this page.

The format is based on `Keep a Changelog`_, and this project adheres to
`Semantic Versioning`_.

v0.1.9 (21 October 2021)
------------------------

This version is compatible with new FIAT raster (xarray) version

Added
^^^^^
- scaling functions for economic and population growth

Fixed
^^^^^
- bugfix resampling in buildings workflow


v0.0.1 (20 May 2021)
--------------------

Initial release of hydromt_fiat

Added
^^^^^

* FiatModel Class with:
* read/write fiat_configuration.xls
* read/write hazard and exposure layers
* copy vulnerability tables
* setup_hazard
* setup_exposure_buildings
* scale_exposure
* buildings workflows

Changed
^^^^^^^


Documentation
^^^^^^^^^^^^^

- Initial docs

.. _Keep a Changelog: https://keepachangelog.com/en/1.0.0/
.. _Semantic Versioning: https://semver.org/spec/v2.0.0.html