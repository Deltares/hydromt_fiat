"""Exposure workflows."""

import logging

import pandas as pd
import xarray as xr

from hydromt_fiat.utils import CURVE, EXPOSURE_LINK
from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray

__all__ = ["exposure_grid_data"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_grid_data(
    grid_like: xr.Dataset | None,
    exposure_data: dict[str, xr.DataArray],
    exposure_linking: pd.DataFrame,
) -> xr.Dataset:
    """Read and transform exposure grid data.

    Parameters
    ----------
    grid_like : xr.Dataset | None
        Xarray dataset that is used to transform exposure data with. If set to None,
        the first data array in exposure_data is used to transform the data.
    exposure_data : dict[str, xr.DataArray]
        Dictionary containing name of exposure file and associated data
    exposure_linking : pd.DataFrame
        Table containing the names of the exposure files and corresponding
        vulnerability curves.

    Returns
    -------
    xr.Dataset
        Transformed and unified exposure grid
    """
    exposure_dataarrays = []

    # Check if linking table columns are named according to convention
    for col_name in [EXPOSURE_LINK, CURVE]:
        if col_name not in exposure_linking.columns:
            raise ValueError(
                f"Missing column, '{col_name}' in exposure grid linking table"
            )

    # Loop through the the supplied data arrays
    for da_name, da in exposure_data.items():
        if da_name not in exposure_linking[EXPOSURE_LINK].values:
            fn_damage = da_name
            logger.warning(
                f"Exposure file name, '{da_name}', not found in linking table."
                f" Setting damage curve name attribute to '{da_name}'."
            )
        else:
            fn_damage = exposure_linking.loc[
                exposure_linking[EXPOSURE_LINK] == da_name, CURVE
            ].values[0]

        # Process the arrays, .e.g make gdal compliant
        da = _process_dataarray(da=da, da_name=da_name)
        da = da.assign_attrs({"fn_damage": fn_damage})
        exposure_dataarrays.append(da)

    return _merge_dataarrays(grid_like=grid_like, dataarrays=exposure_dataarrays)
