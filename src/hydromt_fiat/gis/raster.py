"""Raster functions."""

import logging
import math

import numpy as np
import xarray as xr
from affine import Affine

__all__ = ["expand_raster_to_bounds"]

logger = logging.getLogger(f"hydromt.{__name__}")


def expand_raster_to_bounds(
    ds: xr.Dataset | xr.DataArray,
    bbox: tuple[float] | np.ndarray,
) -> xr.Dataset | xr.DataArray:
    """Expand a raster to (beyond) the borders of a bounding box.

    When expanded, the new raster will be aligned with the old one.

    Parameters
    ----------
    da : xr.DataArray
        The input raster dataset.
    bounds : tuple[float] | np.ndarray
        The bounds to which to expand the raster.

    Returns
    -------
    xr.DataArray
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
