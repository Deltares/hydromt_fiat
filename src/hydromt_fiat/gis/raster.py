"""Raster functions."""

import logging
import math

import geopandas as gpd
import numpy as np
import xarray as xr
from affine import Affine
from hydromt.gis import full
from hydromt.model.processes.grid import grid_from_rasterdataset
from rasterio.enums import MergeAlg

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


def rasterize(
    geom: gpd.GeoDataFrame,
    column: str,
    ds_like: xr.DataArray | xr.Dataset,
    *,
    dtype=np.float32,
    nodata=np.nan,
    fill_value=np.nan,
    all_touched: bool = True,
    method: str = "add",
) -> xr.DataArray:
    """Rasterize geometrie column value into a data array.

    This will be a newly created data array based on a similar raster (`ds_like`).

    Parameters
    ----------
    geom : gpd.GeoDataFrame
        The geometry data.
    column : str
        The column values to rasterize.
    ds_like : xr.DataArray | xr.Dataset
        The blueprint data array.
    dtype : _type_, optional
        The data type of the output data array, by default np.float32.
    nodata : _type_, optional
        The nodata value, by default np.nan.
    fill_value : _type_, optional
        The fill value. This value is ignored when `method` is set to 'add'.
        By default np.nan.
    all_touched : bool, optional
        Whether to add the value to every cell touched by the geometry or only when the
        centroid of the geometry is covered by the geometry. By default True.
    method : str, optional
        The method of which to merge values when rasterizing values into the same
        cell, choose between 'add' and 'replace'. By default 'add'.

    Returns
    -------
    xr.DataArray
        The resulting rasterized data.
    """
    if column not in geom.columns:
        raise ValueError(f"'{column}' column not found in exposure geometry data")

    temp_nodata = nodata
    if method == "add":
        temp_nodata = 0
        fill_value = 0
    # Create the new data array based on the existing raster definition
    da = full(
        coords={d: c for d, c in ds_like.coords.items() if d in ds_like.dims},
        nodata=temp_nodata,
        fill_value=fill_value,
        dtype=dtype,
        crs=ds_like.raster.crs,
        name="data",
        lazy=True,
    )
    # Rasterize it
    da = da.raster.rasterize(
        geom,
        col_name=column,
        nodata=temp_nodata,
        all_touched=all_touched,
        dtype=dtype,
        merge_alg=getattr(MergeAlg, method),
    )

    # Return the nodata setting to the one provided
    da = da.raster.mask_nodata(nodata)

    # Return the rasterized data
    return da
