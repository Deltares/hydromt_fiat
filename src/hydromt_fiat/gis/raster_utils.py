"""Raster utility."""

import xarray as xr
from hydromt.gis import utm_crs
from rasterio.warp import calculate_default_transform


def cell_size(
    ds: xr.Dataset | xr.DataArray,
) -> float:
    """Calculate the cell area of the raster."""
    transform = ds.raster.transform
    if ds.raster.crs.is_geographic:
        crs = utm_crs(ds.raster.bounds)
        transform = calculate_default_transform(
            src_crs=ds.raster.crs,
            dst_crs=crs,
            width=ds.raster.width,
            height=ds.raster.height,
            *ds.raster.bounds,
        )
    return abs(transform[0] * transform[4])


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
