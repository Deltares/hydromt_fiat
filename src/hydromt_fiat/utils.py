"""HydroMT-FIAT utility."""

import logging
from typing import Literal

from pint import Quantity, UnitRegistry
from pint.facets.plain import PlainQuantity

__all__ = ["create_query"]

# GLOBAL STRINGS
## BASE
ANALYSIS = "analysis"
CONFIG = "config"
CURVE = "curve"
DAMAGE = "damage"
EVENT = "event"
EXPOSURE = "exposure"
FILE = "file"
FN = "fn"
GEOM = "geom"
GRID = "grid"
HAZARD = "hazard"
MAX = "max"
MODEL = "model"
NAME = "name"
OBJECT = "object"
OUTPUT = "output"
PATH = "path"
REGION = "region"
RISK = "risk"
RP = "rp"
SETTINGS = "settings"
SRS = "srs"
TYPE = "type"
VULNERABILITY = "vulnerability"

## Delft-FIAT
EXPOSURE_GEOM = f"{EXPOSURE}.{GEOM}"
EXPOSURE_GEOM_FILE = f"{EXPOSURE_GEOM}.{FILE}"
EXPOSURE_GRID = f"{EXPOSURE}.{GRID}"
EXPOSURE_GRID_FILE = f"{EXPOSURE_GRID}.{FILE}"
EXPOSURE_GRID_SETTINGS = f"{EXPOSURE_GRID}.{SETTINGS}"
FN_CURVE = f"{FN}_{CURVE}"
HAZARD_FILE = f"{HAZARD}.{FILE}"
HAZARD_RP = f"{HAZARD}.{RP}"
HAZARD_SETTINGS = f"{HAZARD}.{SETTINGS}"
CALC = "calc"
MODEL_CALC = f"{MODEL}.{CALC}"
MODEL_RISK = f"{MODEL}.{RISK}"
MODEL_TYPE = f"{MODEL}.{TYPE}"
OUTPUT_GEOM_NAME = f"{OUTPUT}.{GEOM}.{NAME}"
OUTPUT_GRID_NAME = f"{OUTPUT}.{GRID}.{NAME}"
OUTPUT_PATH = f"{OUTPUT}.{PATH}"
VAR_AS_BAND = "var_as_band"
VULNERABILITY_FILE = f"{VULNERABILITY}.{FILE}"

## HydroMT-FIAT
COST_TYPE = f"cost_{TYPE}"
CURVE_ID = f"{CURVE}_id"
CURVES = f"{CURVE}s"
EXPOSURE_LINK = f"{EXPOSURE}_link"
EXPOSURE_TYPE = f"{EXPOSURE}_{TYPE}"
IDENTIFIERS = "identifiers"
OBJECT_TYPE = f"{OBJECT}_{TYPE}"
OBJECT_ID = f"{OBJECT}_id"
SUBTYPE = f"sub{TYPE}"

# Unit database init
UNIT_REGISTRY: UnitRegistry = UnitRegistry()  # type: ignore[type-arg]

# calc
CALC_METHODS = {
    "water_depth": "flood.depth",
    "water_level": "flood.level",
}

logger = logging.getLogger(f"hydromt.{__name__}")


def create_query(**kwargs) -> str:
    """Generate a query for a pandas DataFrame.

    Parameters
    ----------
    kwargs : dict
        Keyword arguments that are processed to a query. N.b. these are additive.

    Returns
    -------
    str
        A string containing the pandas dataframe query.
    """
    sub_queries = []
    for key, item in kwargs.items():
        if isinstance(item, (list, tuple)):
            sub_queries.append(f"{key} in {str(item)}")
            continue
        if isinstance(item, str):
            item = f"'{item}'"
        sub_queries.append(f"{key} == {str(item)}")
    query = " and ".join(sub_queries)
    return query


def standard_unit(unit: str) -> PlainQuantity | Quantity:  # type: ignore[type-arg]
    """Translate unit to standard unit for category.

    Parameters
    ----------
    unit : Scalar
        A unit.

    Returns
    -------
    Quantity
        Quantity holding the standard unit and conversion magnitude.
    """
    # Check for the dafault unit
    quantity = UNIT_REGISTRY(unit)
    default_quantity = quantity.to_base_units()
    if default_quantity.magnitude == 1:
        return quantity

    # Setup for scaling
    logger.warning(
        f"Given unit ({str(quantity.units)}) does not match \
the standard unit ({str(default_quantity.units)}) \
for {str(quantity.units.dimensionality)}"
    )
    return default_quantity


def get_calculation_method(hazard_type: Literal["flood_depth", "flood_level"]) -> str:
    """Generate the calculation string for a given hazard type.

    Parameters
    ----------
    hazard_type : str
        The type of hazard, e.g. "flood_depth" or "flood_level".

    Returns
    -------
    str
        The model calculation string, e.g. "flood.depth" or "flood.level".
    """
    if hazard_type not in CALC_METHODS:
        raise ValueError(
            f"Unsupported hazard type: {hazard_type}. "
            f"Supported types are: {list(CALC_METHODS.keys())}"
        )
    return CALC_METHODS[hazard_type]
