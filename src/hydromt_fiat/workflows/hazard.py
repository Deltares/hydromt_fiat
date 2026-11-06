"""Hazard workflows."""

import logging
from typing import Any

import xarray as xr

from hydromt_fiat.gis.raster import merge_rasters
from hydromt_fiat.settings.hazard import Hazard
from hydromt_fiat.utils import (
    ANALYSIS,
    EVENT,
    RISK,
    RP,
    TYPE,
    WATER__DEPTH,
    standard_unit,
)

__all__ = ["hazard_setup"]

logger = logging.getLogger(f"hydromt.{__name__}")


def infer_hazard_attrs(
    data: xr.Dataset,
    settings: Hazard | None = None,
) -> dict[str, Any]:
    """Infer hazard data (settings) attributes.

    Parameters
    ----------
    data : xr.Dataset
        The hazard data.
    settings : Hazard | None, optional
        The attributes currently present in the settings file, by default None.

    Returns
    -------
    dict[str, Any]
        The attributes.
    """
    attrs = {}
    # First really set a default inferred guess
    for var in data.data_vars:
        # Update the attributes
        attrs[var] = dict(type=WATER__DEPTH)
    # If nothing to be done, return
    if settings is None:
        return attrs
    for var in settings.variables:
        # There is not data to support it, continue
        if var.name not in data.data_vars:
            continue
        attrs[var.name] = var.model_dump(exclude_none=True)
    return attrs


def hazard_setup(
    hazard_data: dict[str, xr.DataArray],
    hazard_type: str,
    *,
    grid_like: xr.Dataset | None = None,
    return_periods: list[int] | None = None,
    risk: bool = False,
    unit: str = "m",
) -> tuple[xr.Dataset, dict[str, Any]]:
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
    tuple[xr.Dataset, dict[str, Any]]
        Unified xarray dataset containing the hazard data and its variable settings.
    """
    logger.info(f"Processing {hazard_type} hazard data")
    hazard_dataarrays = []
    ds_attrs = {}
    for idx, (da_name, da) in enumerate(hazard_data.items()):
        da.name = da_name

        # Check for unit
        conversion = standard_unit(unit)
        da *= conversion.magnitude

        attrs: dict[str, Any] = {
            TYPE: hazard_type,
        }
        if risk:
            assert return_periods is not None
            attrs[RP] = return_periods[idx]
        ds_attrs[da_name] = attrs

        # Set the event data arrays to the hazard grid component
        da = da.assign_attrs(attrs)
        # Set the nodata value and mask to -9999, which seems a good default
        da = da.raster.mask_nodata(-9999)
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
    return ds, ds_attrs
