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
    exposure_linking: pd.DataFrame | None,
) -> gpd.GeoDataFrame:
    """_summary_.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        _description_
    exposure_type_column : str
        _description_
    vulnerability : pd.DataFrame
        _description_
    exposure_link_data : pd.DataFrame | None
        _description_

    Returns
    -------
    gpd.GeoDataFrame
        _description_
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
    # Also drop the remaining unused columns
    exposure_linking = exposure_linking[[exposure_type_column, "object_type"]]

    # Link the data into a new column
    exposure_data = pd.merge(
        exposure_data,
        exposure_linking,
        on=exposure_type_column,
        how="inner",
        validate="many_to_many",
    )

    # Get the unique exposure types
    headers = vulnerability["exposure_type"]
    if "subtype" in vulnerability:
        headers = vulnerability["exposure_type"] + "_" + vulnerability["subtype"]

    # Go through the unique new headers
    for header in headers.unique().tolist():
        link = vulnerability[headers == header][["link", "curve_id"]]
        link.rename(
            {"link": "object_type", "curve_id": f"fn_{header}"},
            axis=1,
            inplace=True,
        )
        # And merge the data
        exposure_data = exposure_data.merge(link, on="object_type")

    # Reset the index as default for object_id
    exposure_data.reset_index(names="object_id", inplace=True)

    return exposure_data


def exposure_add_columns(
    exposure_data: pd.DataFrame,
    columns: list[str],
    values: int | float | np.ndarray,
) -> gpd.GeoDataFrame:
    """_summary_.

    Parameters
    ----------
    exposure_data : pd.DataFrame
        _description_
    columns : list[str]
        _description_
    values : int | float | list | np.ndarray
        _description_

    Returns
    -------
    gpd.GeoDataFrame
        _description_
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
of the values ({len(values)})."
        )

    # Set the values directly from the ndarray
    exposure_data[columns] = values

    return exposure_data
