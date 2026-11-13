"""Hazard workflows."""

import logging
from typing import Any

import xarray as xr

from hydromt_fiat.settings.hazard import Hazard
from hydromt_fiat.utils import (
    DEFAULT,
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
    hazard_data: xr.DataArray,
    hazard_type: str,
    *,
    name: str = DEFAULT,
    grid_like: xr.Dataset | None = None,
    return_period: float | int | None = None,
    unit: str = "m",
) -> tuple[xr.Dataset, dict[str, Any]]:
    """Read and transform hazard data.

    Parameters
    ----------
    hazard_data : xr.DataArray
        The hazard data.
    hazard_type : str
        Type of hazard.
    name : str, optional
        The name of the hazard data being set up.
    grid_like : xr.Dataset | None
        Grid dataset that serves as an example dataset for transforming the input data.
        By default None.
    return_period : float | int, optional
        The return period of the data when , by default None.
    unit : str, optional
        The unit which the hazard data is in, by default 'm'.

    Returns
    -------
    tuple[xr.DataArray, dict[str, Any]]
        Unified xarray dataarray containing the hazard data and its variable settings.
    """
    logger.info(f"Processing {hazard_type} hazard data")
    attrs = {}
    hazard_data.name = name

    # Check for unit
    conversion = standard_unit(unit)
    hazard_data *= conversion.magnitude

    attrs: dict[str, Any] = {
        TYPE: hazard_type,
    }
    if return_period is not None:
        attrs[RP] = return_period

    # Set the event data arrays to the hazard grid component
    hazard_data = hazard_data.assign_attrs(attrs)
    # Set the nodata value and mask to -9999, which seems a good default
    hazard_data = hazard_data.raster.mask_nodata(-9999)

    # Reproject to gridlike
    if grid_like is not None:
        hazard_data = hazard_data.raster.reproject_like(ds_like=grid_like)

    # Return the dataset
    return hazard_data, attrs
