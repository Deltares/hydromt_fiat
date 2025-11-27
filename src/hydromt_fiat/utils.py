"""HydroMT-FIAT utility."""

import logging
from itertools import islice
from pathlib import Path
from typing import Any

from barril.units import Scalar, UnitDatabase

__all__ = ["create_query"]

# Global strings
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
OBJECT = "object"
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
MODEL_RISK = f"{MODEL}.{RISK}"
MODEL_TYPE = f"{MODEL}.{TYPE}"
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
UNIT_DATABASE = UnitDatabase.GetSingleton()

logger = logging.getLogger(f"hydromt.{__name__}")


def create_query(
    **kwargs: dict[str, Any],
) -> str:
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
        Scaling factor in Scalar structure (unitless).
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


def directory_tree(
    dir_path: Path,
    level: int = -1,
    limit_to_directories: bool = False,
    length_limit: int = 1000,
) -> None:
    """Create a visual tree of the contents of a directory.

    With many thanks to this post:
    https://stackoverflow.com/questions/9727673/list-directory-tree-structure-in-python
    """
    # Specific characters
    space = "    "
    branch = "│   "
    tee = "├── "
    last = "└── "

    # Ensure typing
    dir_path = Path(dir_path)
    files = 0
    directories = 0

    # Nested function for looping through the file and directories
    def inner(dir_path: Path, prefix: str = "", level=-1):
        nonlocal files, directories
        if not level:
            return  # 0, stop iterating
        # Only spit out directories
        if limit_to_directories:
            contents = [d for d in dir_path.iterdir() if d.is_dir()]
        else:
            contents = list(dir_path.iterdir())
        pointers = [tee] * (len(contents) - 1) + [last]
        # Move recursively through the directories
        for pointer, path in zip(pointers, contents):
            if path.is_dir():
                yield prefix + pointer + path.name
                directories += 1
                extension = branch if pointer == tee else space
                # Move through all on level deeper
                yield from inner(path, prefix=prefix + extension, level=level - 1)
            elif not limit_to_directories:
                yield prefix + pointer + path.name
                files += 1

    # Print the top level
    print(dir_path.name)
    iterator = inner(dir_path, level=level)
    for line in islice(iterator, length_limit):
        print(line)  # The contents
    print(f"\n{directories} directories" + (f", {files} files" if files else ""))
