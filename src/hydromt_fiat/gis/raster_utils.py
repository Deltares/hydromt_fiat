"""Raster utility."""

import xarray as xr


def check_spatial(ds: xr.Dataset) -> bool:
    """Check whether it's a spatial dataset."""
    try:
        ds.raster.set_spatial_dims()
        ds.raster.res
    except ValueError:
        return False
    else:
        return True


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
    if check_spatial(ds) and ds.raster.res[1] > 0:
        ds = ds.raster.flipud()
    return ds
