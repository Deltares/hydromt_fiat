"""Calculate max potential damage based on exposure type."""

import geopandas as gpd
import pandas as pd
from hydromt.gis import utm_crs

from hydromt_fiat.utils import create_query


def max_monetary_damage(
    exposure_data: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    exposure_type: str,
    vulnerability: pd.DataFrame,
    **select: dict,
) -> gpd.GeoDataFrame:
    """_summary_.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        _description_
    table_of_costs : pd.DataFrame
        _description_

    Returns
    -------
    gpd.GeoDataFrame
        _description_
    """
    if exposure_cost_table is None:
        raise ValueError("Exposure costs table cannot be None.")

    # Create a query from the kwargs
    query = create_query(**select)
    exposure_cost_table = exposure_cost_table.query(query)

    if len(exposure_cost_table) == 0:
        raise ValueError(f"Select kwargs ({select}) resulted in no remaining data")

    # Get unique linking names
    unique_link = vulnerability.link.unique().tolist()
    # Transpose the cost table
    exposure_cost_table = exposure_cost_table.T.reset_index(names="object_type")
    # Index the cost table
    exposure_cost_table = exposure_cost_table[
        exposure_cost_table["object_type"].isin(unique_link)
    ]

    # Get the area, make sure its a projected crs
    old_crs = exposure_data.crs
    if old_crs.is_geographic:
        crs = utm_crs(exposure_data.total_bounds)
        exposure_data.to_crs(crs, inplace=True)
    area = exposure_data.area

    headers = vulnerability[vulnerability["exposure_type"] == exposure_type]
    headers = headers["subtype"].unique().tolist()

    for header in headers:
        # Get the costs per object
        costs_per = (
            exposure_data["object_type"]
            .to_frame()
            .merge(
                exposure_cost_table,
                on="object_type",
            )
        )
        costs_per.drop("object_type", axis=1, inplace=True)
        costs_per = costs_per.squeeze()
        # Multiply by the area
        costs_per *= area

        exposure_data[f"max_{exposure_type}_{header}"] = costs_per.astype(float)

    return exposure_data
