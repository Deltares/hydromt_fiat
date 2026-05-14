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
    UNIT_REGISTRY,
    create_query,
    standard_unit,
)

__all__ = ["max_value"]

logger = logging.getLogger(f"hydromt.{__name__}")

_AREA_TYPES = {"Polygon", "MultiPolygon"}
_LENGTH_TYPES = {"LineString", "MultiLineString"}
_OBJECT_TYPES = {"Point", "MultiPoint"}

# Maps human shorthand like "m2", "km3", "ft2" to Pint-compatible "m**2".
_PINT_POWER_RE = re.compile(r"(?<=[a-zA-Z])(\d+)$")

_AREA_DIM = UNIT_REGISTRY("m**2").dimensionality
_LENGTH_DIM = UNIT_REGISTRY("m").dimensionality

# Used when a cost table has no `unit` metadata. Treated as currency/area; the
# component falls back to area-basis math, matching the pre-refactor default.
_DEFAULT_CELL_UNIT = "$/m2"


def _to_pint(unit: str) -> str:
    """Translate human shorthand (e.g. 'm2') to Pint syntax ('m**2')."""
    return _PINT_POWER_RE.sub(r"**\1", unit)


def _parse_cell_unit(cell_unit: str) -> tuple[str, str]:
    """Split a cost-cell unit string into ``(numerator, denominator)``.

    Examples
    --------
    ``'$/m2'``           → ``('$', 'm2')``
    ``'EUR/m**2'``       → ``('EUR', 'm**2')``
    ``'no_people/m2'``   → ``('no_people', 'm2')``
    ``'EUR'``            → ``('EUR', '')``        — per-object value
    ``''``               → ``('', '')``           — caller substitutes default
    """
    if "/" not in cell_unit:
        return cell_unit.strip(), ""
    num, denom = cell_unit.split("/", 1)
    return num.strip(), denom.strip()


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
            "Split the dataset by geometry type."
        )
    return buckets.pop()


def _check_alignment(basis: str, denom: str) -> None:
    """Ensure the cost-cell denominator matches the geometric basis."""
    if basis == "object":
        if denom:
            raise ValueError(
                f"Point geometry but cost-cell unit has a denominator "
                f"('/{denom}'). Use a per-object unit (e.g. '$') instead."
            )
        return
    if denom == "":
        # Per-object cost on polygon/line is allowed — factor will be 1.
        return
    dim = UNIT_REGISTRY(_to_pint(denom)).dimensionality
    if basis == "area" and dim != _AREA_DIM:
        raise ValueError(
            f"Polygon geometry but cost-cell denominator '{denom}' is not "
            f"an area unit. Expected something like 'm2' or 'km**2'."
        )
    if basis == "length" and dim != _LENGTH_DIM:
        raise ValueError(
            f"Line geometry but cost-cell denominator '{denom}' is not "
            f"a length unit. Expected something like 'm' or 'km'."
        )


def _geometric_factor(
    exposure_data: gpd.GeoDataFrame,
    *,
    basis: str,
    denom: str,
) -> pd.Series:
    """Compute the per-object factor in the cost table's denominator unit.

    For per-object costs (empty denom or point basis) the factor is 1.0.
    Otherwise the geometry is taken in UTM (m² for areas, m for lengths) and
    converted into ``denom`` by dividing by the base-SI magnitude of one
    ``denom`` (e.g. 10⁶ for ``km**2``).
    """
    if basis == "object" or denom == "":
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

    raw = projected.area if basis == "area" else projected.length

    base_per_denom = standard_unit(_to_pint(denom)).magnitude
    if base_per_denom != 1.0:
        logger.warning(
            f"Converting geometry to '{denom}' (dividing by {base_per_denom})."
        )
    return raw / base_per_denom


def max_value(
    exposure_data: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    exposure_type: str,
    vulnerability: pd.DataFrame,
    exposure_cost_link: pd.DataFrame | None = None,
    **select,
) -> gpd.GeoDataFrame:
    """Determine the maximum per-object value for an exposure dataset.

    The maximum value is ``factor * cost``. ``factor`` is the object's area,
    length, or 1.0 — inferred from the exposure dataset's geometry. The cost
    table's full cell unit (e.g. ``'$/m2'``, ``'no_people/m2'``, ``'EUR'``) is
    read from ``exposure_cost_table.attrs['unit']``; the numerator (value
    unit) is left for the caller to persist, the denominator is used here to
    scale the geometric factor.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        The existing exposure data.
    exposure_cost_table : pd.DataFrame
        The cost table. ``attrs['unit']`` should hold the full cell unit
        (e.g. ``'$/m2'``); falls back to ``'$/m2'`` when absent.
    exposure_type : str
        Type of exposure data, e.g. ``'damage'``.
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
        The resulting exposure data with the maximum value column(s) included.
    """
    if exposure_cost_table is None:
        raise ValueError("Exposure costs table cannot be None")

    cell_unit = exposure_cost_table.attrs.get("unit") or _DEFAULT_CELL_UNIT
    _, denom = _parse_cell_unit(cell_unit)
    basis = _detect_basis(exposure_data)
    _check_alignment(basis, denom)

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

    # Compute the per-object factor in the cost-table's denominator unit.
    # Reprojection (when needed) happens on a copy so the caller's CRS is not
    # mutated.
    factor = _geometric_factor(exposure_data, basis=basis, denom=denom)

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
