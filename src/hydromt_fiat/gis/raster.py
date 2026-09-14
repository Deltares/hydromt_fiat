"""Raster functions."""

import logging
import math

import numpy as np
import xarray as xr
from affine import Affine
from hydromt.model.processes.grid import grid_from_rasterdataset

__all__ = ["expand_raster_to_bounds"]

logger = logging.getLogger(f"hydromt.{__name__}")


def expand_raster_to_bounds(
    ds: xr.Dataset,
    bbox: tuple[float] | np.ndarray,
) -> xr.Dataset:
    """Expand a raster to (beyond) the borders of a bounding box.

    When expanded, the new raster will be aligned with the old one.

    Parameters
    ----------
    da : xr.Dataset
        The input raster dataset.
    bounds : tuple[float] | np.ndarray
        The bounds to which to expand the raster.

    Returns
    -------
    xr.Dataset
        An expanded raster.
    """
    logger.info("Checking raster extent versus region bounding box")
    # Get some metadata
    old_bounds = [round(float(item), 4) for item in ds.raster.bounds]
    bounds = list(ds.raster.bounds)
    shape = [ds[ds.raster.x_dim].size, ds[ds.raster.y_dim].size]

    check = False
    for idx in range(4):
        if not idx // 2:  # Minimum side (xmin, ymin)
            side_check = bounds[idx] <= bbox[idx]
            sign = -1
        else:  # Maximum sides (xmax, ymax)
            side_check = bounds[idx] >= bbox[idx]
            sign = 1
        if side_check:  # It checks out, so return
            continue
        check = True
        offset = abs(bounds[idx] - bbox[idx])
        offset = math.ceil(offset / abs(ds.raster.res[idx % 2]))
        bounds[idx] += offset * abs(ds.raster.res[idx % 2]) * sign
        shape[idx % 2] += offset

    if not check:
        return ds

    # Some logging
    logger.warning("Raster smaller than the region bounding box")

    # Metadata for building the geotransform
    dx, dy = ds.raster.res
    xsign = int(dx / abs(dx))
    ysign = int(dy / abs(dy))
    # New geotransform
    new_transform = Affine(
        dx,
        ds.raster.rotation,
        bounds[(1 - xsign)],
        ds.raster.rotation,
        dy,
        bounds[(1 - ysign) + 1],
    )
    bounds_repr = [round(float(item), 4) for item in bounds]
    logger.info(f"Expanding raster from {old_bounds} to {bounds_repr}")
    # Reproject the data to the new transform
    ds = ds.raster.reproject(
        dst_transform=new_transform,
        dst_width=shape[0],
        dst_height=shape[1],
        method="nearest",  # Same resolution and location, so nearest is the way to go
    )
    return ds


def merge_rasters(
    dataarrays: list[xr.DataArray],
    grid_like: xr.Dataset | xr.DataArray | None = None,
) -> xr.Dataset:
    """Merge multiple DataArrays into one.

    Parameters
    ----------
    dataarrays : list[xr.DataArray]
        The dataarrays.
    grid_like : xr.Dataset | xr.DataArray
        The data to which the dataarrays are reprojected to.

    Returns
    -------
    xr.Dataset
        The resulting merge dataset.
    """
    # if no grid_like, take the first of the arrays
    if grid_like is None:
        grid_like = dataarrays[0]

    # Set to a dataset as this is need for from_rasterdataset
    if not isinstance(grid_like, xr.Dataset):
        grid_like = grid_like.to_dataset()

    # Reproject if necessary
    for idx, da in enumerate(dataarrays):
        dataarrays[idx] = grid_from_rasterdataset(grid_like=grid_like, ds=da)

    ds = xr.merge(dataarrays)
    ds.attrs = {}  # Ensure that the dataset doesnt copy a merged instance of
    # the data variables' attributes

    # Return the data
    return ds
