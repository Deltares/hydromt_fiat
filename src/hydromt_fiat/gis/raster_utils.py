"""Raster utility."""

import xarray as xr


def force_ns(
    ds: xr.Dataset | xr.DataArray,
):
    """Force a raster in north-south orientation.

    Parameters
    ----------
    ds : xr.Dataset | xr.DataArray
        The input dataset to check.
    """
    if ds.raster.res[1] > 0:
        ds = ds.raster.flipud()
    return ds
