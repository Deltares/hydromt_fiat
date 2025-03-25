"""Exposure workflows."""

import geopandas as gpd
import pandas as pd

__all__ = ["exposure_geometries"]


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
    pass
