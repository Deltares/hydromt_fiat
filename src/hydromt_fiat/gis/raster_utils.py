"""Raster utility."""

import xarray as xr


def force_ns(
    ds: xr.Dataset,
) -> xr.Dataset:
    """Force a raster in north-south orientation.

    Parameters
    ----------
    ds : xr.Dataset | xr.DataArray
        The input dataset to check.

    Returns
    -------
    xr.Dataset | xr.DataArray
        Data in north-south orientation.
    """
    if ds.raster.res[1] > 0:
        ds = ds.raster.flipud()
    return ds
