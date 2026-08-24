"""Calculate max potential damage based on exposure type."""

import logging

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely.geometry as sg
from hydromt.gis import utm_crs

from hydromt_fiat.utils import (
    COST__TYPE,
    IMPACT__SUBTYPE,
    MAX,
    OBJECT__TYPE,
    VALUE,
    create_query,
)
from hydromt_fiat.workflows.impact import filter_impact

__all__ = ["max_value"]

logger = logging.getLogger(f"hydromt.{__name__}")


def get_geometry_type(
    gdf: gpd.GeoDataFrame,
):
    types = set(gdf.geom_type.unique())
    if types <= {sg.Polygon.__name__, sg.MultiPolygon.__name__}:
        return 2
    elif types <= {sg.LineString.__name__, sg.MultiLineString.__name__}:
        return 1
    elif types <= {sg.Point.__name__, sg.MultiPoint.__name__}:
        return 0
    else:
        raise ValueError(f"Unsupported geometry types: {types}")


def spatial_dimensions(
    exposure_data: gpd.GeoDataFrame,
):
    # Ensure the geometry is a non geographic CRS
    if exposure_data.crs is not None and exposure_data.crs.is_geographic:
        crs = utm_crs(exposure_data.total_bounds)
        exposure_data.to_crs(crs, inplace=True)

    # Get the geometry type
    geom_type = get_geometry_type(exposure_data)

    # Return the appropriate spatial dimension based on the geometry type
    match geom_type:
        case 0:
            raise ValueError("Point geometries do not have a spatial dimension")
        case 1:
            return exposure_data.length
        case 2:
            return exposure_data.area


def process_cost_table(
    exposure_cost_table: pd.DataFrame | dict[str, float | int],
    **select,
) -> pd.DataFrame:
    """Process the exposure cost table data.

    Parameters
    ----------
    exposure_cost_table : pd.DataFrame | dict[str, float  |  int]
        The exposure cost table data, which can be provided as a DataFrame
        or a dictionary. The dictionary should have the object types as keys and the
        corresponding cost values as values.
    **select : dict, optional
        Keyword arguments to filter the exposure cost table.

    Returns
    -------
    pd.DataFrame
        The processed exposure cost table as a DataFrame.
    """
    # If the table is in dict format, convert it to a DataFrame
    if isinstance(exposure_cost_table, dict):
        exposure_cost_table = pd.DataFrame.from_dict(
            exposure_cost_table, orient="index", columns=[VALUE]
        ).reset_index(names=COST__TYPE)
        # Return the dataframe
        return exposure_cost_table

    # Create a query from the kwargs
    if len(select) != 0:
        query = create_query(**select)
        exposure_cost_table = exposure_cost_table.query(query)
        # Check if the resulting DataFrame is empty after selection
        if len(exposure_cost_table) == 0:
            raise ValueError(f"Select kwargs ({select}) resulted in no remaining data")
        # Transpose the cost table, rename index to object_type to easily merge
        # This is not the object type, but the specific max costs of that element
        exposure_cost_table = exposure_cost_table.T.reset_index(names=COST__TYPE)

    return exposure_cost_table


def max_value(
    exposure_data: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    impact_type: str,
    vulnerability: pd.DataFrame,
    per_unit: bool = True,
    exposure_cost_link: pd.DataFrame | None = None,
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
    # Select based on the impact type(s)
    vulnerability = filter_impact(
        vulnerability=vulnerability,
        impact_type=impact_type,
    )

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
    size = pd.Series(np.ones(exposure_data.shape[0]))
    if per_unit:
        size = spatial_dimensions(exposure_data)

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
        # Multiply by the size of the object
        costs_per *= size[mask].values

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


def max_value_direct(
    exposure_data: gpd.GeoDataFrame,
    value: float | int,
    impact_type: str,
    impact_subtype: str | None = None,
    per_unit: bool = True,
) -> gpd.GeoDataFrame:
    """Set the max value from a single value directly.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        The exposure data.
    value : float | int
        The maximum value.
    impact_type : str
        The impact type.
    impact_subtype : str | None, optional
        The impact subtype, by default None.
    per_unit : bool, optional
        Whether or not to apply the value per unit area, by default True.

    Returns
    -------
    gpd.GeoDataFrame
        The resulting exposure data with the maximum damage included.
    """
    # Get the area, make sure its a projected crs
    size = pd.Series(np.ones(exposure_data.shape[0]))
    if per_unit:
        size = spatial_dimensions(exposure_data)
    return size
