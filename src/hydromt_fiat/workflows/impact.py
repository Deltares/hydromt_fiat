"""Some small impact functions."""

import logging

import numpy as np
import pandas as pd

from hydromt_fiat.utils import IMPACT__TYPE

__all__ = ["filter_impact"]

logger = logging.getLogger(f"hydromt.{__name__}")


def filter_impact(
    vulnerability: pd.DataFrame,
    impact_type: str | list[str],
) -> pd.DataFrame:
    """Filter the vulnerability identifiers based on impact type.

    Parameters
    ----------
    vulnerability : pd.DataFrame
        The vulnvulnerability identifiers.
    impact_type : str | list[str]
        The impact type(s).

    Returns
    -------
    pd.DataFrame
        Filtered identifiers.
    """
    # Typing
    if not isinstance(impact_type, list):
        impact_type = [impact_type]
    impact_type_ar = np.array(impact_type)

    msg = "No data found in the vulnerability identifiers for these \
impact types {types}"
    # Filter
    vulnerability = vulnerability[vulnerability[IMPACT__TYPE].isin(impact_type_ar)]
    if vulnerability.empty:
        raise ValueError(msg.format(types=impact_type))
    check = np.isin(impact_type_ar, vulnerability[IMPACT__TYPE])
    if not check.all():
        logger.warning(msg.format(types=impact_type_ar[~check].tolist()))
    # Return
    return vulnerability
