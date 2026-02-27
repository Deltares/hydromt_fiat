"""Hazard workflows."""

import logging
from typing import Any

import xarray as xr

from hydromt_fiat.utils import ANALYSIS, EVENT, RISK, RP, TYPE, standard_unit
from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray

__all__ = ["hazard_setup"]

logger = logging.getLogger(f"hydromt.{__name__}")


def hazard_setup(
    grid_like: xr.Dataset | None,
    hazard_data: dict[str, xr.DataArray],
    hazard_type: str,
    *,
    return_periods: list[int] | None = None,
    risk: bool = False,
    unit: str = "m",
) -> xr.Dataset:
    """Read and transform hazard data.

    Parameters
    ----------
    grid_like : xr.Dataset | None
        Grid dataset that serves as an example dataset for transforming the input data.
    hazard_data : dict[str, xr.DataArray]
        The hazard data in a dictionary with the names of the datasets as keys.
    hazard_type : str
        Type of hazard.
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
    hazard_dataarrays = []
    for idx, (da_name, da) in enumerate(hazard_data.items()):
        da = _process_dataarray(da=da, da_name=da_name)

        # Check for unit
        conversion = standard_unit(unit)
        da *= conversion.magnitude

        attrs: dict[str, Any] = {
            "name": da_name,
        }
        if risk:
            assert return_periods is not None
            attrs[RP] = return_periods[idx]

        # Set the event data arrays to the hazard grid component
        da = da.assign_attrs(attrs)

        hazard_dataarrays.append(da)
        logger.info(f"Added {hazard_type} hazard map: {da_name}")

    # Reproject to gridlike
    ds = _merge_dataarrays(grid_like=grid_like, dataarrays=hazard_dataarrays)

    attrs = {
        TYPE: hazard_type,
        ANALYSIS: EVENT,
    }
    if risk:
        attrs[ANALYSIS] = RISK
    ds = ds.assign_attrs(attrs)

    return ds
