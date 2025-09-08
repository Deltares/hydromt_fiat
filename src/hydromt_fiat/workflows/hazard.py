"""Hazard workflows."""

import logging

import xarray as xr
from barril.units import Scalar

from hydromt_fiat.utils import standard_unit
from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray

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
    if return_periods is None and not risk:
        return_periods = [""] * len(hazard_data)
    for return_period, (da_name, da) in zip(return_periods, hazard_data.items()):
        da = _process_dataarray(da=da, da_name=da_name)

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

    # Reproject to gridlike
    ds = _merge_dataarrays(grid_like=grid_like, dataarrays=hazard_dataarrays)

    attrs = {
        "type": hazard_type,
        "analysis": "event",
    }
    if risk:
        attrs["analysis"] = "risk"
    ds = ds.assign_attrs(attrs)

    return ds
