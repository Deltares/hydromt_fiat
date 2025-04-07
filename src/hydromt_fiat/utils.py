"""HydroMT-FIAT utility."""

import logging

from barril.units import Scalar, UnitDatabase

__all__ = ["create_query"]

UNIT_DATABASE = UnitDatabase.GetSingleton()

logger = logging.getLogger(f"hydromt.{__name__}")


def create_query(
    **kwargs: dict,
) -> str:
    """Generate a query for a pandas DataFrame.

    Parameters
    ----------
    kwargs : dict
        Keyword arguments that are processed to a query. N.b. these are additive.

    Returns
    -------
    str
        A string containing the pandas dataframe query
    """
    query = ""
    idx = 0
    for key, item in kwargs.items():
        if idx != 0:
            query += " and "
        idx += 1
        if isinstance(item, (list, tuple)):
            query += f"{key} in {str(item)}"
            continue
        if isinstance(item, str):
            item = f"'{item}'"
        query += f"{key} == {str(item)}"
    return query


def standard_unit(unit: Scalar) -> Scalar:
    """Translate unit to standard unit for category.

    Accepted units are listed on the website of barril:
    https://barril.readthedocs.io/en/latest/units.html

    Parameters
    ----------
    unit : Scalar
        A unit.

    Returns
    -------
    Scalar
        Scaling factor in Scalar structure (unitless)
    """
    # Check for the dafault unit
    default_unit = UNIT_DATABASE.GetDefaultUnit(unit.category)
    if default_unit == unit.unit:
        return unit

    # Setup for scaling
    default_scalar = Scalar(1.0, default_unit)
    logger.warning(
        f"Given unit ({unit.unit}) does not match \
the standard unit ({default_unit}) for {unit.category}"
    )
    translate = unit / default_scalar

    return translate
