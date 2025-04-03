"""Exposure workflows."""

import logging

import geopandas as gpd
import pandas as pd

__all__ = ["exposure_geom_linking"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_geom_linking(
    exposure_data: gpd.GeoDataFrame,
    exposure_type_column: str,
    vulnerability: pd.DataFrame,
    *,
    exposure_link_data: pd.DataFrame | None,
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
    if exposure_link_data is None:
        logger.warning(
            "No exposure link table provided, \
defaulting to exposure data object type"
        )
        exposure_link_data = pd.DataFrame(
            {
                exposure_type_column: exposure_data[exposure_type_column].values,
                "object_type": exposure_data[exposure_type_column].values,
            }
        )
    if exposure_type_column not in exposure_link_data:
        raise KeyError(f"{exposure_type_column} not found in the provided linking data")

    # Make sure that there are no duplicated in the linking
    exposure_link_data = exposure_link_data.drop_duplicates(
        exposure_type_column,
        keep="first",
    )
    # Also drop the remaining unused columns
    exposure_link_data = exposure_link_data[[exposure_type_column, "object_type"]]

    # Link the data into a new column
    exposure_data = pd.merge(
        exposure_data,
        exposure_link_data,
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

    return exposure_data
