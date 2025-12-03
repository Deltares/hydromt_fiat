"""Raster utility."""

import numpy as np
import xarray as xr
from affine import Affine
from hydromt.gis import full_from_transform, full_like
from pyproj.crs import CRS


def _grid(
    grid: xr.DataArray | None = None,
    da_like: xr.DataArray | None = None,
    transform: Affine | None = None,
    shape: tuple | None = None,
    crs: CRS | int | str | None = None,
) -> xr.DataArray:
    """Determine the grid the rasterize the vector data in."""
    if grid is not None:
        return grid
    if da_like is not None:
        grid = full_like(other=da_like, nodata=np.nan)
    elif transform is not None and shape is not None:
        grid = full_from_transform(
            transform=transform,
            shape=shape,
            nodata=np.nan,
            crs=crs,
        )
    else:
        raise ValueError("Insufficient input for determining grid")

    return grid


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
