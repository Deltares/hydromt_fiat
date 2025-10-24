"""Exposure geometry workflows."""

import logging

import geopandas as gpd
import numpy as np
import numpy.typing as npt
import pandas as pd

from hydromt_fiat.utils import (
    CURVE_ID,
    EXPOSURE_LINK,
    EXPOSURE_TYPE,
    OBJECT_ID,
    OBJECT_TYPE,
    SUBTYPE,
)

__all__ = [
    "exposure_add_columns",
    "exposure_setup",
    "exposure_vulnerability_link",
]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_setup(
    exposure_data: gpd.GeoDataFrame,
    exposure_type_column: str,
    *,
    exposure_linking: pd.DataFrame | None = None,
    exposure_type_fill: str | None = None,
) -> gpd.GeoDataFrame:
    """Prep the raw exposure data for later fuctions/ methods.

    Here the exposure type can be mapped for better linking later on.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        The raw exposure data.
    exposure_type_column : str
        The name of column that specifies the exposure type, e.g. occupancy type.
    exposure_linking : pd.DataFrame, optional
        A custom mapping to table to first translate the exposure types in order to
        better link with the vulnerability data. A translation layer really.
        By default None
    exposure_type_fill : str, optional
        Value to which missing entries in the exposure type column will be mapped to,
        if provided. By default None

    Returns
    -------
    gpd.GeoDataFrame
        The resulting exposure data.
    """
    logger.info("Setting up the exposure data for further use")
    # Some checks
    if exposure_type_column not in exposure_data:
        raise KeyError(f"{exposure_type_column} not found in the exposure data")
    if exposure_linking is None:
        logger.warning(
            "No exposure link table provided, \
defaulting to exposure data object type"
        )
        exposure_linking = pd.DataFrame(
            {
                exposure_type_column: exposure_data[exposure_type_column].values,
                OBJECT_TYPE: exposure_data[exposure_type_column].values,
            }
        )
    if exposure_type_column not in exposure_linking:
        raise KeyError(f"{exposure_type_column} not found in the provided linking data")

    # Make sure that there are no duplicated in the linking
    exposure_linking = exposure_linking.drop_duplicates(
        exposure_type_column,
        keep="first",
    )
    # Drop the row with None as key, prevents duplicates later
    exposure_linking = exposure_linking.dropna(subset=exposure_type_column)
    # Also drop the remaining unused columns
    exposure_linking = exposure_linking[[exposure_type_column, OBJECT_TYPE]]

    # Set the nodata fill
    if exposure_type_fill is not None:
        exposure_linking.loc[len(exposure_linking), :] = [None, exposure_type_fill]

    # Store the length of the data
    data_or_size = len(exposure_data)

    # Link the data into a new column
    exposure_data = pd.merge(
        exposure_data,
        exposure_linking,
        on=exposure_type_column,
        how="inner",
        validate="many_to_many",
    )
    data_m_size = len(exposure_data)

    # Log a warning when certain features could not be merged
    if data_m_size != data_or_size:
        logger.warning(
            f"{data_or_size - data_m_size} features could not be internally linked, \
these features are removed"
        )

    # Return the data
    return exposure_data


def exposure_vulnerability_link(
    exposure_data: gpd.GeoDataFrame,
    vulnerability: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Link the exposure data to the vulnerability data.

    I.e. link the curve id's of the vulnerability to the exposure types.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        The raw exposure data.
    vulnerability : pd.DataFrame
        The vulnerability identifier table to link up with.

    Returns
    -------
    gpd.GeoDataFrame
        The resulting exposure data linked with the vulnerability data.
    """
    logger.info("Linking the exposure data with the vulnerability data")
    # Get the unique exposure types
    headers = vulnerability[EXPOSURE_TYPE]
    if SUBTYPE in vulnerability:
        headers = vulnerability[EXPOSURE_TYPE] + "_" + vulnerability[SUBTYPE]

    # Set the current size for a check later on
    data_m_size = len(exposure_data)
    # Go through the unique new headers
    header_list = headers.unique().tolist()
    for header in header_list:
        link = vulnerability[headers == header][[EXPOSURE_LINK, CURVE_ID]]
        link.rename(
            {EXPOSURE_LINK: OBJECT_TYPE, CURVE_ID: f"fn_{header}"},
            axis=1,
            inplace=True,
        )
        # And merge the data
        exposure_data = exposure_data.merge(
            link.drop_duplicates(subset=OBJECT_TYPE),
            on=OBJECT_TYPE,
            how="left",
        )

    # Remove the features that don't have any linking to the vulnerability
    exposure_data.dropna(
        subset=[f"fn_{item}" for item in header_list],
        how="all",
        inplace=True,
    )

    # Check the length after vulerability merging
    data_v_size = len(exposure_data)
    if data_v_size != data_m_size:
        logger.warning(
            f"{data_m_size - data_v_size} features could not be linked to \
vulnerability data, these were removed"
        )

    # Reset the index as default for object_id
    if OBJECT_ID not in exposure_data.columns:
        exposure_data.reset_index(names=OBJECT_ID, inplace=True)

    return exposure_data


def exposure_add_columns(
    exposure_data: gpd.GeoDataFrame,
    columns: list[str],
    values: int
    | float
    | str
    | list[int | float | str]
    | npt.NDArray[np.int64 | np.float64 | np.str_],
) -> gpd.GeoDataFrame:
    """Add columms to an existing exposure dataset.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        The exposure dataset.
    columns : list[str]
        List of names to be added as columns.
    values : int | float | str | list | np.ndarray
        The value(s) be set.

    Returns
    -------
    gpd.GeoDataFrame
        The exposure data with the added columns.
    """
    if isinstance(values, (int, float, str, list)):
        if not isinstance(values, list):
            values = [values] * len(columns)
        for column, value in zip(columns, values):
            exposure_data[column] = value
        return exposure_data

    if len(columns) != values.shape[1]:
        raise ValueError(
            f"Length of the columns ({len(columns)}) is not the same as the length \
of the values ({values.shape[1]})."
        )

    # Set the values directly from the ndarray
    exposure_data[columns] = values

    return exposure_data
