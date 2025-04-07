"""Exposure workflows."""

import logging

import pandas as pd
import xarray as xr

from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray

__all__ = ["exposure_grid_data"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_grid_data(
    grid_like: xr.Dataset | None,
    exposure_files: dict[str, xr.DataArray],
    linking_table: pd.DataFrame,
) -> xr.Dataset:
    """Read and transform exposure grid data.

    Parameters
    ----------
    grid_like : xr.Dataset | None
        Xarray dataset that is used to transform exposure data with. If set to None,
            the first data array in exposure_files is used to transform the data.
    exposure_files : dict[str, xr.DataArray]
        Dictionary containing name of exposure file and associated data
    linking_table : pd.DataFrame
        Table containing the names of the exposure files and corresponding
        vulnerability curves.

    Returns
    -------
    xr.Dataset
        Transformed and unified exposure grid
    """
    exposure_dataarrays = []
    exposure_col = "type"
    vulnerability_col = "curve_id"

    for exposure_fn, da in exposure_files.items():
        if exposure_fn not in linking_table[exposure_col].values:
            fn_damage = exposure_fn
            logger.warning(
                f"Exposure file name, '{exposure_fn}', not found in linking table."
                f" Setting damage curve name attribute to '{exposure_fn}'."
            )
        else:
            fn_damage = linking_table.loc[
                linking_table[exposure_col] == exposure_fn, vulnerability_col
            ].values[0]
        da = _process_dataarray(da=da, da_name=exposure_fn)
        da = da.assign_attrs({"fn_damage": fn_damage})
        exposure_dataarrays.append(da)

    return _merge_dataarrays(grid_like=grid_like, dataarrays=exposure_dataarrays)
