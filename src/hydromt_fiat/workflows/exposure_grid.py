"""Exposure workflows."""

import logging

import dask.array as dar
import numpy as np
import pandas as pd
import xarray as xr

from hydromt_fiat.gis.raster import merge_rasters
from hydromt_fiat.gis.raster_utils import cell_size
from hydromt_fiat.utils import (
    AREA__SQM,
    CATEGORIES,
    CURVE,
    EXPOSURE__TYPE,
    FN_CURVE,
    IMPACT__SUBTYPE,
    OBJECT__TYPE,
    TYPE,
    standard_unit,
)

__all__ = ["exposure_grid_default_setup"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_grid_default_setup(
    exposure_data: dict[str, xr.DataArray],
    vulnerability: pd.DataFrame,
    grid_like: xr.Dataset | None = None,
    exposure_link: pd.DataFrame | None = None,
) -> xr.Dataset:
    """Process and transform exposure grid data.

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


def exposure_grid_categorized_setup(
    exposure_data: xr.DataArray,
    vulnerability: pd.DataFrame,
    name: str,
    grid_like: xr.Dataset | xr.DataArray | None = None,
) -> xr.Dataset:
    """Process categorized gridded exposure.

    Parameters
    ----------
    exposure_data : xr.DataArray
        The exposure data consisting of integers representing the individual
        categories. Only integer based data is accepted.
    vulnerability : pd.DataFrame
        The vulnerability identifiers. The curve identifiers in the 'curve' column, if
        they are of the integer type, are taken to match against the value in the
        exposure data.
    name : str
        The name of the exposure data.
    grid_like : xr.Dataset | xr.DataArray | None, optional
        A grid (definition) to reproject/ resample the data to in order to match
        the resolution and extent, by default None.

    Returns
    -------
    xr.Dataset
        The processed categorized gridded exposure data.
    """
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
        logger.warning(f"The following categories have no correspoding curve: {disc}")

    # Set some metadata
    exposure_data.attrs.update(
        {
            CATEGORIES: unique.tolist(),
            AREA__SQM: cell_size(exposure_data),
            TYPE: "tabled",
        },
    )

    # Return the merged data (symbolic, but can still reproject)
    return merge_rasters(dataarrays=[exposure_data], grid_like=grid_like)


def exposure_grid_category_values(
    exposure_data: xr.DataArray,
    table: pd.DataFrame | None = None,
    default: float | int = 100,
    unit: str = "m**2",
) -> xr.Dataset:
    """Create a dataset of linked values corresponding to the exposure data.

    Parameters
    ----------
    exposure_data : xr.DataArray
        The exposure data.
    table : pd.DataFrame | None, optional
        A dataframe containing the values linked to the categories in the exposyre data.
        If not provided, all values are set to the default, by default None.
    default : float | int, optional
        The default value when the table is not provided or has missing values compared
        to the categorized exposure data, by default 100.
    unit : str, optional
        The unit (per) of the values, if not the standard (e.g. m**2) the values are
        translated to the standard unit of that category (e.g. m**2 for length squared).
        By default "m**2".

    Returns
    -------
    xr.Dataset
        The dataset containing the values linked to the categories, the categories are
        an integer based dimension.
    """
    # Check for the categories attribute
    if CATEGORIES not in exposure_data.attrs:
        raise AttributeError(
            "'categories' attribute should be present in the exposure DataArray"
        )

    # Get some metadata
    name = exposure_data.name
    cat = exposure_data.attrs[CATEGORIES]
    table_size = max(cat) + 1

    # Add the coordinate for the table values based on the maximum value
    coord_name = f"{name}_tc"
    ds = xr.Dataset(
        coords={coord_name: range(0, table_size + 1)},
    )
    ds[coord_name] = ds[coord_name].astype(exposure_data.dtype)

    # If no table provided set a default variables
    if table is None:
        logger.info(
            f"No table values were provided, defaulting to the default value: {default}"
        )
        ds = ds.assign(
            {f"{name}_def": ((coord_name), np.ones(table_size + 1) * default)},
        )
        return ds

    # Otherwise move through the table
    table.drop_duplicates(subset=name, inplace=True)
    table.set_index(name, inplace=True)
    table = table[table.index < table_size]
    # Set a warning for those values falling that do not have a value associated with it
    disc = np.setdiff1d(cat, table.index).tolist()
    if len(disc) > 0:
        logger.warning(
            f"The following categories have no corresponding value: {disc}, these will \
be set to the default value of {default}"
        )

    # Loop though the columns
    conversion = standard_unit(unit)
    for col in table.columns:
        data = np.ones(table_size + 1, dtype=np.float32) * default
        data[table.index] = table[col].values * conversion.magnitude
        ds = ds.assign({f"{name}_{col}": ((coord_name), data)})

    # return the dataset
    return ds
