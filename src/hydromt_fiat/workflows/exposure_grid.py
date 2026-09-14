"""Exposure workflows."""

import logging

import dask.array as dar
import numpy as np
import pandas as pd
import xarray as xr

from hydromt_fiat.gis.raster import merge_rasters
from hydromt_fiat.utils import (
    CATEGORIES,
    CURVE,
    EXPOSURE__TYPE,
    FN_CURVE,
    IMPACT__SUBTYPE,
    OBJECT__TYPE,
    TYPE,
)

__all__ = ["exposure_grid_default_setup"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_grid_default_setup(
    exposure_data: dict[str, xr.DataArray],
    vulnerability: pd.DataFrame,
    grid_like: xr.Dataset | None = None,
    exposure_link: pd.DataFrame | None = None,
) -> xr.Dataset:
    """Read and transform exposure grid data.

    Parameters
    ----------
    exposure_data : dict[str, xr.DataArray]
        Dictionary containing name of exposure file and associated data
    vulnerability : pd.DataFrame
        A Table containing valid vulnerability curve id's an their
        presumed link to the exposure.
    grid_like : xr.Dataset | None
        Xarray dataset that is used to transform exposure data with. If set to None,
        the first data array in exposure_data is used to transform the data.
        By default None.
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

    # Get the unique exposure types. Only append the subtype where a row
    # actually has one; rows without it keep the bare object type as header.
    headers = vulnerability[OBJECT__TYPE].astype(str)
    if IMPACT__SUBTYPE in vulnerability:
        sub = vulnerability[IMPACT__SUBTYPE]
        headers = headers.mask(
            sub.notna() & ~(sub == ""), headers + "_" + sub.astype(str)
        )

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
        da = da.assign_attrs({FN_CURVE: fn_curve})
        exposure_dataarrays.append(da)

    if len(exposure_dataarrays) == 0:
        return xr.Dataset()

    return merge_rasters(dataarrays=exposure_dataarrays, grid_like=grid_like)


def exposure_grid_table_based_setup(
    exposure_data: xr.DataArray,
    vulnerability: pd.DataFrame,
    name: str,
    grid_like: xr.Dataset | xr.DataArray | None = None,
) -> xr.Dataset:
    # Adjust the data slightly
    exposure_data.name = name
    exposure_data = exposure_data.raster.mask_nodata(0)

    # Get all integer based columns
    curves = (
        vulnerability.loc[vulnerability[CURVE].str.fullmatch(r"-?\d+"), CURVE]
        .astype(int)
        .values
    )

    # Get the unique numbers
    unique = dar.unique(exposure_data.data).compute()

    # Inform the user that certain types are not available, both ways
    disc = np.setdiff1d(unique, curves).tolist()
    if len(disc) > 0:
        logger.warning(f"The following values have no correspoding curve: {disc}")

    # Set some metadata
    exposure_data.attrs.update({CATEGORIES: unique.tolist(), TYPE: "tabled"})

    # Return the merged data (symbolic, but can still reproject)
    return merge_rasters(dataarrays=[exposure_data], grid_like=grid_like)


def exposure_grid_table_values(
    exposure_data: xr.DataArray,
    values: pd.DataFrame,
    default: float | int,
) -> xr.Dataset:
    # Check for the categories attribute
    if CATEGORIES not in exposure_data.attrs:
        raise AttributeError("")

    # Set some metadata
    name = exposure_data.name
    table_size = max(exposure_data.attrs[CATEGORIES]) + 1

    ds = xr.Dataset(
        coords={f"{name}_tc": range(0, table_size + 1)},
    )
    ds = ds.assign({"avg": ((f"{name}_tc"), np.ones(table_size + 1) * default)})

    # return the dataset
    return ds
