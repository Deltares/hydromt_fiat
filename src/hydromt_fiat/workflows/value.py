"""Calculate max potential value per exposure object."""

import logging
import re
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
    standard_unit,
)

__all__ = ["max_value"]

logger = logging.getLogger(f"hydromt.{__name__}")

_VALID_BASES = ("area", "length", "object")
_AREA_TYPES = {"Polygon", "MultiPolygon"}
_LENGTH_TYPES = {"LineString", "MultiLineString"}
_OBJECT_TYPES = {"Point", "MultiPoint"}

# Maps human shorthand like "m2", "km3", "ft2" to Pint-compatible "m**2".
_PINT_POWER_RE = re.compile(r"(?<=[a-zA-Z])(\d+)$")


def _to_pint(unit: str) -> str:
    """Translate human shorthand (e.g. 'm2') to Pint syntax ('m**2')."""
    return _PINT_POWER_RE.sub(r"**\1", unit)


def _detect_basis(exposure_data: gpd.GeoDataFrame) -> str:
    """Infer the geometric basis (area/length/object) from geometry types."""
    geom_types = set(exposure_data.geom_type.dropna().unique())
    if not geom_types:
        raise ValueError("Cannot detect basis: exposure_data has no geometries")
    buckets = set()
    if geom_types & _AREA_TYPES:
        buckets.add("area")
    if geom_types & _LENGTH_TYPES:
        buckets.add("length")
    if geom_types & _OBJECT_TYPES:
        buckets.add("object")
    unknown = geom_types - (_AREA_TYPES | _LENGTH_TYPES | _OBJECT_TYPES)
    if unknown:
        raise ValueError(
            f"Cannot detect basis: unsupported geometry types {sorted(unknown)}"
        )
    if len(buckets) != 1:
        raise ValueError(
            f"Mixed geometry types in exposure_data: {sorted(geom_types)}. "
            "Provide basis= explicitly or split the dataset."
        )
    return buckets.pop()


def _geometric_factor(
    exposure_data: gpd.GeoDataFrame,
    basis: str,
    unit: str,
) -> pd.Series:
    """Compute the per-object geometric factor (area, length, or 1.0)."""
    if basis == "object":
        if unit != "m2":
            logger.info(f"basis='object': unit '{unit}' ignored")
        return pd.Series(1.0, index=exposure_data.index)

    crs = exposure_data.crs
    if crs is not None and crs.is_geographic:
        minx, miny, maxx, maxy = exposure_data.total_bounds
        zone_min = utm_crs((minx, miny, minx, miny))
        zone_max = utm_crs((maxx, maxy, maxx, maxy))
        if zone_min != zone_max:
            logger.warning(
                f"Exposure data bounds span more than one UTM zone "
                f"({zone_min.to_authority()} vs {zone_max.to_authority()}); "
                "reprojecting to a single zone may introduce "
                "area/length distortion."
            )
        projected = exposure_data.to_crs(utm_crs(exposure_data.total_bounds))
    else:
        projected = exposure_data

    if basis == "area":
        factor = projected.area
    else:
        factor = projected.length

    return factor * standard_unit(_to_pint(unit)).magnitude


def max_value(
    exposure_data: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    exposure_type: str,
    vulnerability: pd.DataFrame,
    exposure_cost_link: pd.DataFrame | None = None,
    *,
    basis: str | None = None,
    unit: str = "m2",
    **select,
) -> gpd.GeoDataFrame:
    """Determine the maximum per-object value for an exposure dataset.

    The maximum value is ``factor * cost``, where ``factor`` is the object's
    area, length, or 1.0 depending on ``basis``, optionally scaled to the
    requested ``unit``. The cost-table denominator must match ``unit`` (e.g.
    EUR/m² for ``unit='m2'``).

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
    basis : {'area', 'length', 'object'}, optional
        How to derive the per-object geometric factor. If None (default), the
        basis is auto-detected from ``exposure_data.geom_type``: polygons
        → 'area', lines → 'length', points → 'object'. Mixed geometries raise.
        When given explicitly the value is honoured without cross-checking the
        geometry.
    unit : str, optional
        Unit of the geometric denominator in the cost table. Default 'm2'.
        Ignored when ``basis == 'object'``.
    **select : dict, optional
        Keyword arguments to select data from the cost table.
        The key corresponds to the column and the value to value in that column.

    Returns
    -------
    gpd.GeoDataFrame
        The resulting exposure data with the maximum value column(s) included.
    """
    if exposure_cost_table is None:
        raise ValueError("Exposure costs table cannot be None")

    # Resolve basis (auto-detect or validate user input)
    if basis is None:
        basis = _detect_basis(exposure_data)
    elif basis not in _VALID_BASES:
        raise ValueError(f"basis must be one of {_VALID_BASES}, got {basis!r}")

    # Create a query from the kwargs
    if len(select) != 0:
        query = create_query(**select)
        exposure_cost_table = exposure_cost_table.query(query)

    if len(exposure_cost_table) == 0:
        raise ValueError(f"Select kwargs ({select}) resulted in no remaining data")

    # If no cost link table is defined, define it self
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

    # Compute the per-object factor (area / length / 1.0) in the requested unit.
    # Reprojection (when needed) happens on a copy so the caller's CRS is not
    # mutated.
    factor = _geometric_factor(exposure_data, basis=basis, unit=unit)

    # Loop through the headers to set the max value per subtype (or not)
    for header in headers:
        data = exposure_data[COST_TYPE] + header
        # Get the costs per object
        costs_per = data.to_frame().merge(exposure_cost_table, on=COST_TYPE)
        costs_per.drop(COST_TYPE, axis=1, inplace=True)
        costs_per = costs_per.squeeze()
        # Multiply by the geometric factor
        costs_per *= factor

        exposure_data[f"{MAX}_{exposure_type}{header}"] = costs_per.astype(float)

    # Check data length afterwards
    data_m_size = len(exposure_data)
    if data_or_size != data_m_size:
        logger.warning(
            f"{data_or_size - data_m_size} features could not be linked to the \
damage values, these were removed"
        )

    return exposure_data
