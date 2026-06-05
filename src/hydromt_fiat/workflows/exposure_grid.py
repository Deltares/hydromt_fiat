"""Exposure workflows."""

import logging

import pandas as pd
import xarray as xr

from hydromt_fiat.utils import (
    CURVE,
    EXPOSURE__TYPE,
    FN_CURVE,
    IMPACT__SUBTYPE,
    OBJECT__TYPE,
)
from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray

__all__ = ["exposure_grid_setup"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_grid_setup(
    grid_like: xr.Dataset | None,
    exposure_data: dict[str, xr.DataArray],
    vulnerability: pd.DataFrame,
    exposure_link: pd.DataFrame | None = None,
) -> xr.Dataset:
    """Read and transform exposure grid data.

    Parameters
    ----------
    grid_like : xr.Dataset | None
        Xarray dataset that is used to transform exposure data with. If set to None,
        the first data array in exposure_data is used to transform the data.
    exposure_data : dict[str, xr.DataArray]
        Dictionary containing name of exposure file and associated data
    vulnerability : pd.DataFrame
        A Table containing valid vulnerability curve id's an their
        presumed link to the exposure.
    exposure_link : pd.DataFrame, optional
        Table containing the names of the exposure files and corresponding
        vulnerability curves.

    Returns
    -------
    xr.Dataset
        Transformed and unified exposure grid.
    """
    exposure_dataarrays = []

    # Log the fact that there is not linking table
    if exposure_link is None:
        logger.warning(
            "No exposure linking provided, \
defaulting to the name of the exposure layer"
        )
        # Construct a dummy dataframe from the names
        entries = list(exposure_data.keys())
        exposure_link = pd.DataFrame(
            data={
                EXPOSURE__TYPE: entries,
                OBJECT__TYPE: entries,
            }
        )

    # Check if linking table columns are named according to convention
    for col_name in [EXPOSURE__TYPE, OBJECT__TYPE]:
        if col_name not in exposure_link.columns:
            raise ValueError(
                f"Missing column, '{col_name}' in exposure grid linking table"
            )

    # Get the unique exposure types
    headers = vulnerability[OBJECT__TYPE]
    if IMPACT__SUBTYPE in vulnerability:
        headers = vulnerability[OBJECT__TYPE] + "_" + vulnerability[IMPACT__SUBTYPE]

    # Loop through the the supplied data arrays
    for da_name, da in exposure_data.items():
        if da_name not in exposure_link[EXPOSURE__TYPE].values:
            link_name = da_name
        else:
            link_name = exposure_link.loc[
                exposure_link[EXPOSURE__TYPE] == da_name, OBJECT__TYPE
            ].values[0]

        # Check if in vulnerability curves link table
        link = vulnerability[headers == link_name]
        if link.empty:
            logger.warning(f"Couldn't link '{da_name}' to vulnerability, skipping...")
            continue

        # Get the vulnerability curve ID
        fn_curve = link[CURVE].values[0]

        # Process the arrays, .e.g make gdal compliant
        da = _process_dataarray(da=da, da_name=da_name)
        da = da.assign_attrs({FN_CURVE: fn_curve})
        exposure_dataarrays.append(da)

    if len(exposure_dataarrays) == 0:
        return xr.Dataset()

    return _merge_dataarrays(grid_like=grid_like, dataarrays=exposure_dataarrays)
