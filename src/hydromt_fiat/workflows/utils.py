"""Workflow utilities."""

import logging

import xarray as xr
from hydromt.model.processes.grid import grid_from_rasterdataset

logger = logging.getLogger(f"hydromt.{__name__}")


def _process_dataarray(da: xr.DataArray, da_name: str) -> xr.DataArray:
    # Convert to gdal compliant
    da.encoding["_FillValue"] = None
    da = da.raster.gdal_compliant()
    da = da.rename(da_name)

    # Check if map is rotated and if yes, reproject to a non-rotated grid
    if "xc" in da.coords:
        logger.warning(
            "Hazard grid is rotated. It will be reprojected"
            " to a non rotated grid using nearest neighbor"
            "interpolation"
        )
        da = da.raster.reproject(dst_crs=da.rio.crs)
    if "grid_mapping" in da.encoding:
        _ = da.encoding.pop("grid_mapping")
    return da


def _merge_dataarrays(
    grid_like: xr.Dataset | xr.DataArray | None, dataarrays: list[xr.DataArray]
) -> xr.Dataset:
    if grid_like is None:
        logger.warning(
            "No known grid provided to reproject to, \
defaulting to first specified grid for transform and extent"
        )
        grid_like = dataarrays[0]

    # Reproject to gridlike
    if isinstance(grid_like, xr.DataArray):
        grid_like = grid_like.to_dataset()

    # Reproject if necessary
    for idx, da in enumerate(dataarrays):
        dataarrays[idx] = grid_from_rasterdataset(grid_like=grid_like, ds=da)

    ds = xr.merge(dataarrays)
    ds.attrs = {}  # Ensure that the dataset doesnt copy a merged instance of
    # the data variables' attributes

    # Return the data
    return ds
