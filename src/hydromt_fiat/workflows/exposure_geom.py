"""Exposure geometry workflows."""

import logging

import geopandas as gpd
import numpy as np
import pandas as pd

__all__ = ["exposure_add_columns", "exposure_geom_linking"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_geom_linking(
    exposure_data: gpd.GeoDataFrame,
    exposure_type_column: str,
    vulnerability: pd.DataFrame,
    *,
    exposure_linking: pd.DataFrame | None = None,
    exposure_type_fill: str | None = None,
) -> gpd.GeoDataFrame:
    """Link the raw exposure data to the vulnerability curves.

    I.e. link the curve id's of the vulnerability to the exposure types.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        The raw exposure data.
    exposure_type_column : str
        The name of column that specifies the exposure type, e.g. occupancy type.
    vulnerability : pd.DataFrame
        The vulnerability identifier table to link up with.
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
        The resulting exposure data with links to the vulnerability curves.
    """
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
                "object_type": exposure_data[exposure_type_column].values,
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
    exposure_linking = exposure_linking[[exposure_type_column, "object_type"]]

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

    if data_m_size != data_or_size:
        logger.warning(
            f"{data_or_size - data_m_size} features could not be linked, \
these features are removed"
        )

    # Get the unique exposure types
    headers = vulnerability["exposure_type"]
    if "subtype" in vulnerability:
        headers = vulnerability["exposure_type"] + "_" + vulnerability["subtype"]

    # Go through the unique new headers
    for header in headers.unique().tolist():
        link = vulnerability[headers == header][["exposure_link", "curve_id"]]
        link.rename(
            {"exposure_link": "object_type", "curve_id": f"fn_{header}"},
            axis=1,
            inplace=True,
        )
        # And merge the data
        exposure_data = exposure_data.merge(link, on="object_type")

    # Check the length after vulerability merging
    data_v_size = len(exposure_data)
    if data_v_size != data_m_size:
        logger.warning(
            f"{data_m_size - data_v_size} features could not be linked to \
vulnerability data, these were removed"
        )

    # Reset the index as default for object_id
    exposure_data.reset_index(names="object_id", inplace=True)

    return exposure_data


def exposure_add_columns(
    exposure_data: gpd.GeoDataFrame,
    columns: list[str],
    values: int | float | list | np.ndarray,
) -> gpd.GeoDataFrame:
    """Add columms to an existing exposure dataset.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        The exposure dataset.
    columns : list[str]
        List of names to be added as columns.
    values : int | float | list| np.ndarray
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
