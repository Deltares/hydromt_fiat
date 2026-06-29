"""Hazard workflows."""

import logging
from typing import Any

import xarray as xr
from pint import UnitRegistry

from hydromt_fiat.utils import (
    ANALYSIS,
    EVENT,
    RISK,
    RP,
    TYPE,
    UNIT_REGISTRY,
    standard_unit,
)
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
    unit_default: str | None = None,
    unit_registry: UnitRegistry = UNIT_REGISTRY,  # type: ignore[type-arg]
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
    unit_default : str, optional
        The default unit to translate hazard data to when `unit` is not the
        same. If not provided, the default unit is taken from the `unit_registry`
        for the corresponding category (e.g. 'length' for meters). By default None.
    unit_registry : UnitRegistry, optional
        The unit registry (system) to use when mapping the unit to the default unit
        from the same category. If not provided,
        the default registry is assumed to be that of the metric system.

    Returns
    -------
    xr.Dataset
        Unified xarray dataset containing the hazard data.
    """
    logger.info(f"Processing {hazard_type} hazard data")
    hazard_dataarrays = []
    for idx, (da_name, da) in enumerate(hazard_data.items()):
        da = _process_dataarray(da=da, da_name=da_name)

        # Check for unit
        conversion = standard_unit(unit, registry=unit_registry, default=unit_default)
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
    ds = _merge_dataarrays(grid_like=grid_like, dataarrays=hazard_dataarrays)

    attrs = {
        ANALYSIS: EVENT,
    }
    if risk:
        attrs[ANALYSIS] = RISK
    ds = ds.assign_attrs(attrs)

    return ds
