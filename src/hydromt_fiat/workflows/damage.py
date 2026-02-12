"""Calculate max potential damage based on exposure type."""

import logging
from itertools import product

import geopandas as gpd
import pandas as pd
from hydromt.gis import utm_crs

from hydromt_fiat.utils import (
    COST_TYPE,
    EXPOSURE_LINK,
    EXPOSURE_TYPE,
    MAX,
    OBJECT_TYPE,
    SUBTYPE,
    create_query,
)

__all__ = ["max_monetary_damage"]

logger = logging.getLogger(f"hydromt.{__name__}")


def max_monetary_damage(
    exposure_data: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    exposure_type: str,
    vulnerability: pd.DataFrame,
    exposure_cost_link: pd.DataFrame | None = None,
    **select,
) -> gpd.GeoDataFrame:
    """Determine maximum monetary damage per object.

    The maximum potential monetary damage is calculated based on the area (footprint)
    of the objects. The exposure cost table should therefore contain values per square
    meter.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        The existing exposure data.
    exposure_cost_table : pd.DataFrame
        The cost table.
    exposure_type : str
        Type of exposure data, e.g. 'damage'.
    vulnerability : pd.DataFrame
        The vulnerability identifier table.
    exposure_cost_link : pd.DataFrame, optional
        A linking table to connect the exposure data to the exposure cost data.
        By default None.
    **select : dict, optional
        Keyword arguments to select data from the cost table.
        The key corresponds to the column and the value to value in that column.

    Returns
    -------
    gpd.GeoDataFrame
        The resulting exposure data with the maximum damage included.
    """
    if exposure_cost_table is None:
        raise ValueError("Exposure costs table cannot be None")

    # Create a query from the kwargs
    if len(select) != 0:
        query = create_query(**select)
        exposure_cost_table = exposure_cost_table.query(query)

    if len(exposure_cost_table) == 0:
        raise ValueError(f"Select kwargs ({select}) resulted in no remaining data")

    # If not cost link table is defined, define it self
    if exposure_cost_link is None:
        exposure_cost_link = pd.DataFrame(
            data={
                OBJECT_TYPE: vulnerability[EXPOSURE_LINK].values,
                COST_TYPE: vulnerability[EXPOSURE_LINK].values,
            }
        )

    # Check for the necessary columns
    if not all(item in exposure_cost_link.columns for item in [OBJECT_TYPE, COST_TYPE]):
        raise ValueError(f"Cost link table either missing {OBJECT_TYPE} or {COST_TYPE}")
    # Leave only the necessary columns
    exposure_cost_link = exposure_cost_link[[OBJECT_TYPE, COST_TYPE]]
    exposure_cost_link = exposure_cost_link.drop_duplicates(subset=OBJECT_TYPE)

    # Get the unique headers corresponding to the 'exposure_type'
    if SUBTYPE not in vulnerability.columns:
        headers = [""]
    else:
        headers = vulnerability[vulnerability[EXPOSURE_TYPE] == exposure_type]
        headers = ["_" + str(item) for item in headers[SUBTYPE].unique()]

    # If not headers were found, log and return
    if len(headers) == 0:
        raise ValueError(
            f"Exposure type ({exposure_type}) not found in vulnerability data"
        )

    # Get unique linking names
    unique_link = exposure_cost_link[COST_TYPE].unique().tolist()
    unique_link = [f"{x}{y}" for x, y in product(unique_link, headers)]
    # Transpose the cost table, rename index to object_type to easily merge
    # This is not the object type, but the specific max costs of that element
    exposure_cost_table = exposure_cost_table.T.reset_index(names=COST_TYPE)
    # Index the cost table
    exposure_cost_table = exposure_cost_table[
        exposure_cost_table[COST_TYPE].isin(unique_link)
    ]

    # Link the cost type to the exposure data
    data_or_size = len(exposure_data)  # For size check later
    exposure_data[COST_TYPE] = exposure_data[[OBJECT_TYPE]].merge(
        exposure_cost_link,
        on=OBJECT_TYPE,
        how="inner",
    )[COST_TYPE]

    # Drop the data that cannnot be linked
    exposure_data.dropna(subset=COST_TYPE, inplace=True)

    # Get the area, make sure its a projected crs
    old_crs = exposure_data.crs
    if old_crs.is_geographic:
        crs = utm_crs(exposure_data.total_bounds)
        exposure_data.to_crs(crs, inplace=True)
    area = exposure_data.area

    # Loop through the headers to set the max damage per subtype (or not)
    for header in headers:
        data = exposure_data[COST_TYPE] + header
        # Get the costs per object
        costs_per = data.to_frame().merge(exposure_cost_table, on=COST_TYPE)
        costs_per.drop(COST_TYPE, axis=1, inplace=True)
        costs_per = costs_per.squeeze()
        # Multiply by the area
        costs_per *= area

        exposure_data[f"{MAX}_{exposure_type}{header}"] = costs_per.astype(float)

    # Check data length afterwards
    data_m_size = len(exposure_data)
    if data_or_size != data_m_size:
        logger.warning(
            f"{data_or_size - data_m_size} features could not be linked to the \
damage values, these were removed"
        )

    return exposure_data
