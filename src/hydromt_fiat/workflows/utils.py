"""Workflow utilities."""

import logging

import xarray as xr
from hydromt.model.processes.grid import grid_from_rasterdataset

logger = logging.getLogger(f"hydromt.{__name__}")


def _process_dataarray(da: xr.DataArray, da_name: str) -> xr.DataArray:
    # Convert to gdal compliant
    da.encoding["_FillValue"] = None
    da: xr.DataArray = da.raster.gdal_compliant()
    da = da.rename(da_name)

    # Check if map is rotated and if yes, reproject to a non-rotated grid
    if "xc" in da.coords:
        logger.warning(
            "Hazard map is rotated. It will be reprojected"
            " to a non rotated grid using nearest neighbor"
            "interpolation"
        )
        da: xr.DataArray = da.raster.reproject(dst_crs=da.rio.crs)
    if "grid_mapping" in da.encoding:
        _ = da.encoding.pop("grid_mapping")
    return da


def _merge_dataarrays(
    grid_like: xr.Dataset | None, dataarrays: list[xr.DataArray]
) -> xr.Dataset:
    if grid_like is None:
        logger.warning(
            "grid_like argument not given, defaulting to first grid file in the list"
            " of grids"
        )
        grid_like = dataarrays[0]

    # Reproject to gridlike
    if isinstance(grid_like, xr.DataArray):
        grid_like = grid_like.to_dataset()

    ds = xr.merge(dataarrays)

    # Reproject to gridlike
    return grid_from_rasterdataset(grid_like=grid_like, ds=ds)
