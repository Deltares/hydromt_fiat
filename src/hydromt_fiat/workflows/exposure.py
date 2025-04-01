"""Exposure workflows."""

import logging

import geopandas as gpd
import pandas as pd

__all__ = ["exposure_geometries"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_geometries(
    exposure_data: gpd.GeoDataFrame,
    exposure_type_column: str,
    vulnerability: pd.DataFrame,
    exposure_link_data: pd.DataFrame | None,
):
    """_summary_.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        _description_
    exposure_type_column : str
        _description_
    exposure_link_data : pd.DataFrame | None
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
                "new": exposure_data[exposure_type_column].values,
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
    exposure_link_data = exposure_link_data[[exposure_type_column, "new"]]

    # Link the data into a new column
    exposure_data = pd.merge(
        exposure_data,
        exposure_link_data,
        on=exposure_type_column,
        how="inner",
        validate="many_to_many",
    )
    pass
