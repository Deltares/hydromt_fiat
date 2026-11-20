.. _changelog:

=========
Changelog
=========

Unreleased
==========

Added
-----
- ``VulnerabilityComponent.create_nd`` to build n-dimensional vulnerability curves from
  one dimensional curves, with the combination rules ``product``, ``union``, ``mean``,
  ``geometric``, ``isoline``, ``blend`` and ``anchored``.
- The required ``variables`` settings of the hazard, the vulnerability and the exposure
  grid, mirroring those of Delft-FIAT.
- The required ``vulnerability`` setting per exposure geometry file.
- The ``values`` exposure grid type.
- Reading and writing grids as ``.zarr`` and ``.tif`` files.
- ``scipy`` as a dependency.

Changed
-------
- A ``risk`` model requires a return period (``rp``) for every hazard variable.

Removed
-------
- The model wide ``method`` setting, the method is set per vulnerability dataset.
