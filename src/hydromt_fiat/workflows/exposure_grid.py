"""Exposure workflows."""

import logging

import pandas as pd
import xarray as xr

from hydromt_fiat.utils import CURVE, EXPOSURE_LINK, OBJECT_TYPE, SUBTYPE
from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray

__all__ = ["exposure_grid_setup"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_grid_setup(
    grid_like: xr.Dataset | None,
    exposure_data: dict[str, xr.DataArray],
    vulnerability: pd.DataFrame,
    exposure_linking: pd.DataFrame | None = None,
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
    exposure_linking : pd.DataFrame, optional
        Table containing the names of the exposure files and corresponding
        vulnerability curves.

    Returns
    -------
    xr.Dataset
        Transformed and unified exposure grid.
    """
    exposure_dataarrays = []

    # Log the fact that there is not linking table
    if exposure_linking is None:
        logger.warning(
            "No exposure linking provided, \
defaulting to the name of the exposure layer"
        )
        # Construct a dummy dataframe from the names
        entries = list(exposure_data.keys())
        exposure_linking = pd.DataFrame(
            data={
                EXPOSURE_LINK: entries,
                OBJECT_TYPE: entries,
            }
        )

    # Check if linking table columns are named according to convention
    for col_name in [EXPOSURE_LINK, OBJECT_TYPE]:
        if col_name not in exposure_linking.columns:
            raise ValueError(
                f"Missing column, '{col_name}' in exposure grid linking table"
            )

    # Get the unique exposure types
    headers = vulnerability[EXPOSURE_LINK]
    if SUBTYPE in vulnerability:
        headers = vulnerability[EXPOSURE_LINK] + "_" + vulnerability[SUBTYPE]

    # Loop through the the supplied data arrays
    for da_name, da in exposure_data.items():
        if da_name not in exposure_linking[EXPOSURE_LINK].values:
            link_name = da_name
        else:
            link_name = exposure_linking.loc[
                exposure_linking[EXPOSURE_LINK] == da_name, OBJECT_TYPE
            ].values[0]

        # Check if in vulnerability curves link table
        link = vulnerability[headers == link_name]
        if link.empty:
            logger.warning(f"Couldn't link '{da_name}' to vulnerability, skipping...")
            continue

        # Get the vulnerability curve ID
        fn_damage = link[CURVE].values[0]

        # Process the arrays, .e.g make gdal compliant
        da = _process_dataarray(da=da, da_name=da_name)
        da = da.assign_attrs({"fn_damage": fn_damage})
        exposure_dataarrays.append(da)

    if len(exposure_dataarrays) == 0:
        return xr.Dataset()

    return _merge_dataarrays(grid_like=grid_like, dataarrays=exposure_dataarrays)
