"""Hazard workflows."""

import logging

import xarray as xr
from barril.units import Scalar
from hydromt.model.processes.grid import grid_from_rasterdataset

from hydromt_fiat.utils import standard_unit

__all__ = ["hazard_grid"]

logger = logging.getLogger(f"hydromt.{__name__}")


def hazard_grid(
    grid_like: xr.Dataset | None,
    hazard_data: dict[str : xr.DataArray],
    hazard_type: str,
    *,
    return_periods: list[int] | None = None,
    risk: bool = False,
    unit: str = "m",
) -> xr.Dataset:
    """Parse hazard data files to xarray dataset.

    Parameters
    ----------
    grid_like : xr.Dataset | None
        Grid dataset that serves as an example dataset for transforming the input data
    hazard_data : dict[str:xr.DataArray]
        The hazard data in a dictionary with the names of the datasets as keys.
    hazard_type : str
        Type of hazard
    return_periods : list[int] | None, optional
        List of return periods, by default None
    risk : bool
        Designate hazard files for risk analysis, by default False
    unit : str
        The unit which the hazard data is in, by default 'm'

    Returns
    -------
    xr.Dataset
        Unified xarray dataset containing the hazard data
    """
    hazard_dataarrays = []
    if return_periods is None and not risk:
        return_periods = [""] * len(hazard_data)
    for return_period, (da_name, da) in zip(return_periods, hazard_data.items()):
        # Convert to gdal compliant
        da.encoding["_FillValue"] = None
        da: xr.DataArray = da.raster.gdal_compliant()

        # ensure variable name is lowercase
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

        # Check for unit
        conversion = standard_unit(Scalar(1.0, unit))
        da *= conversion.value

        rp = f"(rp {return_period})" if risk else ""
        logger.info(f"Added {hazard_type} hazard map: {da_name} {rp}")

        attrs = {
            "name": da_name,
        }
        if risk:
            attrs["return_period"] = return_period
        # Set the event data arrays to the hazard grid component
        da = da.assign_attrs(attrs)

        hazard_dataarrays.append(da)

    if grid_like is None:
        grid_like = hazard_dataarrays[0]

    ds = xr.merge(hazard_dataarrays)
    ds.attrs = {}

    # Reproject to gridlike
    if isinstance(grid_like, xr.DataArray):
        grid_like = grid_like.to_dataset()
    ds = grid_from_rasterdataset(grid_like=grid_like, ds=ds)

    attrs = {
        "type": hazard_type,
        "analysis": "event",
    }
    if risk:
        attrs["analysis"] = "risk"
    ds = ds.assign_attrs(attrs)

    return ds
