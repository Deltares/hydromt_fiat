"""Hazard workflows."""

import logging

import xarray as xr
from hydromt.model.processes.grid import grid_from_rasterdataset

__all__ = ["hazard_grid"]


logger = logging.getLogger(f"hydromt.{__name__}")


def hazard_grid(
    grid_like: xr.Dataset | None,
    hazard_data: dict[str : xr.DataArray],
    hazard_type: str,
    *,
    return_periods: list[int] | None = None,
    risk: bool,
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
        Designate hazard files for risk analysis

    Returns
    -------
    xr.Dataset
        Unified xarray dataset containing the hazard data
    """
    hazard_dataarrays = []
    for idx, (da_name, da) in enumerate(hazard_data.items()):
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

        rp = f"(rp {return_periods[idx]})" if risk else ""
        logger.info(f"Added {hazard_type} hazard map: {da_name} {rp}")

        if not risk:
            # Set the event data arrays to the hazard grid component
            da = da.assign_attrs(
                {
                    "name": da_name,
                    "type": hazard_type,
                    "analysis": "event",
                }
            )

        hazard_dataarrays.append(da)
    if grid_like is None:
        grid_like = hazard_dataarrays[0]

    ds = xr.merge(hazard_dataarrays)

    # Reproject to gridlike
    if isinstance(grid_like, xr.DataArray):
        grid_like = grid_like.to_dataset()
    ds = grid_from_rasterdataset(grid_like=grid_like, ds=ds)
    da_names = [d.name for d in hazard_dataarrays]

    if risk:
        ds = ds.assign_attrs(
            {
                "return_period": return_periods,
                "type": hazard_type,
                "name": da_names,
                "analysis": "risk",
            }
        )

    else:
        ds = ds.assign_attrs(
            {"analysis": "event", "type": hazard_type, "name": da_names}
        )
    return ds
