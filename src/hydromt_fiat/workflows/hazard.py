"""Hazard workflows."""

import logging
from typing import Any

import xarray as xr

from hydromt_fiat.gis.raster import merge_rasters
from hydromt_fiat.utils import ANALYSIS, EVENT, RISK, RP, TYPE, standard_unit

__all__ = ["hazard_setup"]

logger = logging.getLogger(f"hydromt.{__name__}")


def hazard_setup(
    hazard_data: dict[str, xr.DataArray],
    hazard_type: str,
    *,
    grid_like: xr.Dataset | None = None,
    return_periods: list[int] | None = None,
    risk: bool = False,
    unit: str = "m",
) -> xr.Dataset:
    """Read and transform hazard data.

    Parameters
    ----------
    hazard_data : dict[str, xr.DataArray]
        The hazard data in a dictionary with the names of the datasets as keys.
    hazard_type : str
        Type of hazard.
    grid_like : xr.Dataset | None
        Grid dataset that serves as an example dataset for transforming the input data.
        By default None.
    return_periods : list[int], optional
        List of return periods, by default None.
    risk : bool, optional
        Designate hazard files for risk analysis, by default False.
    unit : str, optional
        The unit which the hazard data is in, by default 'm'.

    Returns
    -------
    xr.Dataset
        Unified xarray dataset containing the hazard data.
    """
    logger.info(f"Processing {hazard_type} hazard data")
    hazard_dataarrays = []
    for idx, (da_name, da) in enumerate(hazard_data.items()):
        da.name = da_name
        # da = _process_dataarray(da=da, da_name=da_name)

        # Check for unit
        conversion = standard_unit(unit)
        da *= conversion.magnitude

        attrs: dict[str, Any] = {
            "name": da_name,
            TYPE: hazard_type,
        }
        if risk:
            assert return_periods is not None
            attrs[RP] = return_periods[idx]

        # Set the event data arrays to the hazard grid component
        da = da.assign_attrs(attrs)
        hazard_dataarrays.append(da)

    # Reproject to gridlike
    ds = merge_rasters(dataarrays=hazard_dataarrays, grid_like=grid_like)

    # Set the new attributes
    attrs = {
        ANALYSIS: EVENT,
    }
    if risk:
        attrs[ANALYSIS] = RISK
    ds = ds.assign_attrs(attrs)
    # Return the dataset
    return ds
