"""Exposure workflows."""

import logging

import dask.array as dar
import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

from hydromt_fiat.gis.raster import merge_rasters, rasterize
from hydromt_fiat.utils import (
    CATEGORIES,
    CATEGORIZED,
    CURVE,
    DEFAULT,
    EXPOSURE__TYPE,
    FN__CURVE,
    IMPACT__SUBTYPE,
    INDEX,
    OBJECT__TYPE,
    TYPE,
    VALUE,
    standard_unit,
)

__all__ = [
    "exposure_grid_categorized_setup",
    "exposure_grid_category_values",
    "exposure_grid_default_setup",
    "exposure_grid_from_geometries",
]

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
        da.attrs.update(
            {
                FN__CURVE: fn_curve,
                TYPE: DEFAULT,
            },
        )
        # Mask the data to -9999, seems like a good default value
        da = da.raster.mask_nodata(-9999)
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
    exposure_data = exposure_data.astype(np.uint32)

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
            TYPE: CATEGORIZED,
        },
    )

    # Return the merged data (symbolic, but can still reproject)
    return merge_rasters(dataarrays=[exposure_data], grid_like=grid_like)


def exposure_grid_category_values(
    exposure_data: xr.DataArray,
    table: pd.DataFrame | None = None,
    columns: list[str] | str | None = None,
    index_name: str = INDEX,
    default: float | int = 100,
    unit: str = "m**2",
) -> xr.Dataset:
    """Create a dataset of linked values corresponding to the exposure data.

    Parameters
    ----------
    exposure_data : xr.DataArray
        The exposure data.
    table : pd.DataFrame | None, optional
        A dataframe containing the values linked to the categories in the exposure data.
        If not provided, all values are set to the default, by default None.
    columns : list[str] | str, optional
        List of columns to select from the provided table. If not provided, all columns
        from the provided table are used. By Default None.
    index_name : str, optional
        The name of the index column in the table data, if the table data is provided.
        By default 'index'.
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
    coord_name = f"{name}_cat"
    ds = xr.Dataset(
        coords={coord_name: range(table_size)},
    )
    ds[coord_name] = ds[coord_name].astype(exposure_data.dtype)

    # If no table provided set a default variables
    if table is None:
        logger.info(
            f"No table values were provided, defaulting to the default value: {default}"
        )
        data = np.ones(table_size) * default
        data[0] = 0
        ds = ds.assign(
            {f"{name}_{VALUE}": ((coord_name), data)},
        )
        return ds

    # Otherwise move through the table
    table.drop_duplicates(subset=index_name, inplace=True)
    table.set_index(index_name, inplace=True)
    table = table[table.index < table_size]
    # Set a warning for those values falling that do not have a value associated with it
    disc = np.setdiff1d(cat, table.index).tolist()
    if len(disc) > 0:
        logger.warning(
            f"The following categories have no corresponding value: {disc}, these will \
be set to the default value of {default}"
        )

    # Get the columns
    columns = columns or table.columns.to_list()
    # Assert columns type
    if not isinstance(columns, (list, tuple)):
        columns = [columns]
    # Select only those that are actually in the table
    selected_columns = [item for item in columns if item in table.columns]
    if len(selected_columns) == 0:
        raise ValueError(f"{columns} columns no available in provided table data")
    logger.info(
        f"Setting up category values from the following \
table columns: {selected_columns}",
    )

    # Loop though the columns
    conversion = standard_unit(unit)
    for col in selected_columns:
        data = np.ones(table_size, dtype=np.float32) * default
        data[0] = 0
        data[table.index] = table[col].values * conversion.magnitude
        ds = ds.assign({f"{name}_{col}": ((coord_name), data)})

    # return the dataset
    return ds


def exposure_grid_from_geometries(
    exposure_data: gpd.GeoDataFrame,
    column: str,
    curve: str,
    vulnerability: pd.DataFrame,
    ds_like: xr.DataArray | xr.Dataset,
    *,
    mult: float | int = 1,
    add: float | int = 0,
    method: str = "add",
) -> xr.DataArray:
    """Create exposure grid data from geometry data.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        The exposure geometry data.
    column : str
        The column from which the value will be burned in.
    curve : str
        The name of the vulnerability curve identifier.
    vulnerability : pd.DataFrame
        The vulnerability identifiers. The curve identifiers in the 'curve' column, if
        they are of the integer type, are taken to match against the value in the
        exposure data.
    ds_like : xr.DataArray | xr.Dataset
        The raster definition.
    mult : float | int, optional
        The multiplication factor put on top of the burned in values, by default 1.
    add : float | int, optional
        The value added on top of the burned in value, by default 0.
    method : str, optional
        The method of which to merge values when rasterizing values into the same
        cell, choose between 'add' and 'replace'. By default 'add'.

    Returns
    -------
    xr.DataArray
        The resulting array with burned in values.
    """
    da = rasterize(
        geom=exposure_data,
        column=column,
        ds_like=ds_like,
        method=method,
    )
    da.name = VALUE
    # Update values
    da = (da * mult) + add

    # Call the method to setup the data
    ds = exposure_grid_default_setup(
        exposure_data={VALUE: da},
        vulnerability=vulnerability,
        exposure_link=pd.DataFrame({EXPOSURE__TYPE: [VALUE], OBJECT__TYPE: [curve]}),
    )

    # Quick check on the data
    if VALUE not in ds.data_vars:
        raise RuntimeError(f"Could not resolve vulnerability curve: {curve}")

    # Return the array
    return ds[VALUE]
