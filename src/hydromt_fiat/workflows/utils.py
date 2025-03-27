"""Workflow utilities."""

import logging

import xarray as xr

logger = logging.getLogger(f"hydromt.{__name__}")


def _process_grid(da: xr.DataArray, da_name: str) -> xr.DataArray:
    # Convert to gdal compliant
    da.encoding["_FillValue"] = None
    da: xr.DataArray = da.raster.gdal_compliant()
    da = da.rename(da_name)

    # Check if map is rotated and if yes, reproject to a non-rotated grid
    if "xc" in da.coords:
        logger.warning(
            "Hazard map is rotated. It will be reprojected"
            " to a none rotated grid using nearest neighbor"
            "interpolation"
        )
        da: xr.DataArray = da.raster.reproject(dst_crs=da.rio.crs)
    if "grid_mapping" in da.encoding:
        _ = da.encoding.pop("grid_mapping")
    return da
