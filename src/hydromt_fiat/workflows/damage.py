"""Calculate max potential damage based on exposure type."""

import logging

import geopandas as gpd
import numpy as np
import pandas as pd
from hydromt.gis import utm_crs

from hydromt_fiat.utils import (
    COST__TYPE,
    IMPACT__SUBTYPE,
    MAX,
    OBJECT__TYPE,
    create_query,
)
from hydromt_fiat.workflows.impact import filter_impact

__all__ = ["max_monetary_damage"]

logger = logging.getLogger(f"hydromt.{__name__}")


def max_monetary_damage(
    exposure_data: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    impact_type: str,
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
    impact_type : str
        Type of impact, e.g. 'damage' (monetary damage).
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

    # Select based on the impact type(s)
    vulnerability = filter_impact(
        vulnerability=vulnerability,
        impact_type=impact_type,
    )

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
                OBJECT__TYPE: vulnerability[OBJECT__TYPE].values,
                COST__TYPE: vulnerability[OBJECT__TYPE].values,
            }
        )

    # Check for the necessary columns
    if not all(
        item in exposure_cost_link.columns for item in [OBJECT__TYPE, COST__TYPE]
    ):
        raise ValueError(
            f"Cost link table either missing {OBJECT__TYPE} or {COST__TYPE}"
        )
    # Leave only the necessary columns
    exposure_cost_link = exposure_cost_link[[OBJECT__TYPE, COST__TYPE]]
    exposure_cost_link = exposure_cost_link.drop_duplicates(subset=OBJECT__TYPE)

    # Get the unique headers corresponding to the 'exposure_type
    maintypes = vulnerability[OBJECT__TYPE].to_numpy()
    subtypes = np.full(maintypes.size, "")
    if IMPACT__SUBTYPE in vulnerability:
        sub = vulnerability[IMPACT__SUBTYPE]
        subtypes = sub.mask(
            sub.notna() & ~(sub == ""), "_" + sub.astype(str)
        ).to_numpy()
    # Combined as one string
    combined = np.array([f"{x}{y}" for x, y in zip(maintypes, subtypes)])

    # Get unique linking names
    unique_link = np.unique(combined)
    # Transpose the cost table, rename index to object_type to easily merge
    # This is not the object type, but the specific max costs of that element
    exposure_cost_table = exposure_cost_table.T.reset_index(names=COST__TYPE)
    # Index the cost table
    exposure_cost_table = exposure_cost_table[
        exposure_cost_table[COST__TYPE].isin(unique_link)
    ]
    # Get the valid indices the other way around as well
    valid = np.isin(combined, exposure_cost_table[COST__TYPE])

    # Link the cost type to the exposure data
    data_or_size = len(exposure_data)  # For size check later
    exposure_data[COST__TYPE] = exposure_data[[OBJECT__TYPE]].merge(
        exposure_cost_link,
        on=OBJECT__TYPE,
        how="inner",
    )[COST__TYPE]

    # Drop the data that cannnot be linked
    exposure_data.dropna(subset=COST__TYPE, inplace=True)

    # Get the area, make sure its a projected crs
    old_crs = exposure_data.crs
    if old_crs.is_geographic:
        crs = utm_crs(exposure_data.total_bounds)
        exposure_data.to_crs(crs, inplace=True)
    area = exposure_data.area

    # Create the columns
    for st in set(subtypes):
        exposure_data[f"{MAX}_{impact_type}{st}"] = np.nan

    # Loop through the headers to set the max damage per subtype (or not)
    for mt, st in set(zip(maintypes[valid], subtypes[valid])):
        mask = exposure_data[COST__TYPE] == mt
        # Skip if main type (cost type is not found)
        if not any(mask):
            continue
        data = exposure_data[COST__TYPE][mask] + st
        # Get the costs per object
        costs_per = data.to_frame().merge(exposure_cost_table, on=COST__TYPE)
        costs_per.drop(COST__TYPE, axis=1, inplace=True)
        costs_per = costs_per.squeeze()
        # Multiply by the area
        costs_per *= area[mask].values

        # Set the values
        exposure_data.loc[mask, f"{MAX}_{impact_type}{st}"] = costs_per.values.astype(
            np.float64
        )

    # Check data length afterwards
    data_m_size = len(exposure_data)
    if data_or_size != data_m_size:
        logger.warning(
            f"{data_or_size - data_m_size} features could not be linked to the \
damage values, these were removed"
        )

    return exposure_data
