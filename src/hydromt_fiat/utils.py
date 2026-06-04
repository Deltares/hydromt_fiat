"""HydroMT-FIAT utility."""

import logging
from itertools import islice
from pathlib import Path

from pint import Quantity, UnitRegistry
from pint.facets.plain import PlainQuantity

__all__ = ["create_query"]

# GLOBAL STRINGS
## BASE
ANALYSIS = "analysis"
AREA = "area"
CALC = "calc"
CONFIG = "config"
CURVE = "curve"
DAMAGE = "damage"
EVENT = "event"
EXPOSURE = "exposure"
FILE = "file"
FN = "fn"
GEOM = "geom"
GEOMETRY = "geometry"
GRID = "grid"
HAZARD = "hazard"
ID = "id"
IMPACT = "impact"
MAX = "max"
MODEL = "model"
NAME = "name"
OBJECT = "object"
OUTPUT = "output"
PATH = "path"
POST = "post"
REGION = "region"
REGISTRY = "registry"
RISK = "risk"
RP = "rp"
SETTINGS = "settings"
SQUARE = "square"
SRS = "srs"
TYPE = "type"
VERSION = "version"
VULNERABILITY = "vulnerability"

## Delft-FIAT
EXPOSURE_GEOM = f"{EXPOSURE}.{GEOM}"
EXPOSURE_GEOM_FILE = f"{EXPOSURE_GEOM}.{FILE}"
EXPOSURE_GRID = f"{EXPOSURE}.{GRID}"
EXPOSURE_GRID_FILE = f"{EXPOSURE_GRID}.{FILE}"
EXPOSURE_GRID_SETTINGS = f"{EXPOSURE_GRID}.{SETTINGS}"
FLOOD = "flood"
FLOOD_DEPTH = f"{FLOOD}.depth"
FLOOD_LEVEL = f"{FLOOD}.level"
FN_CURVE = f"{FN}_{CURVE}"
HAZARD_FILE = f"{HAZARD}.{FILE}"
HAZARD_RP = f"{HAZARD}.{RP}"
HAZARD_SETTINGS = f"{HAZARD}.{SETTINGS}"
MODEL_CALC = f"{MODEL}.{CALC}"
MODEL_RISK = f"{MODEL}.{RISK}"
MODEL_TYPE = f"{MODEL}.{TYPE}"
OUTPUT_GEOM_NAME = f"{OUTPUT}.{GEOM}.{NAME}"
OUTPUT_GRID_NAME = f"{OUTPUT}.{GRID}.{NAME}"
OUTPUT_PATH = f"{OUTPUT}.{PATH}"
VAR_AS_BAND = "var_as_band"
VULNERABILITY_FILE = f"{VULNERABILITY}.{FILE}"

## HydroMT-FIAT
AREA__SQM = f"{AREA}_sqm"
COST__TYPE = f"cost_{TYPE}"
CURVE__ID = f"{CURVE}_{ID}"
CURVES = f"{CURVE}s"
EXPOSURE__TYPE = f"{EXPOSURE}_{TYPE}"
IDENTIFIERS = "identifiers"
IMPACT__SUBTYPE = f"{IMPACT}_sub{TYPE}"
IMPACT__TYPE = f"{IMPACT}_{TYPE}"
OBJECT__TYPE = f"{OBJECT}_{TYPE}"
OBJECT__ID = f"{OBJECT}_{ID}"
SQUARE__ID = f"{SQUARE}_{ID}"

# Unit database init
UNIT_REGISTRY: UnitRegistry = UnitRegistry()  # type: ignore[type-arg]

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


def standard_unit(
    unit: str,
    default: str | None = None,
) -> PlainQuantity | Quantity:  # type: ignore[type-arg]
    """Translate unit to standard unit for category.

    Parameters
    ----------
    unit : Scalar
        A unit.
    default : str, optional
        A unit to convert to. If None, the standard unit according to pint is taken
        for each category, e.g. 'm/s' for velocity. By default None.

    Returns
    -------
    Quantity
        Quantity holding the standard unit and conversion magnitude.
    """
    # Check for the dafault unit
    quantity = UNIT_REGISTRY(unit)
    default = default or str(UNIT_REGISTRY.get_base_units(unit)[1])
    default_quantity = quantity.to(default)
    if default_quantity.magnitude == 1:
        return quantity

    # Setup for scaling
    logger.warning(
        f"Given unit ({str(quantity.units)}) does not match \
the standard/ default unit ({str(default_quantity.units)}) \
for {str(quantity.units.dimensionality)}"
    )
    return default_quantity


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
