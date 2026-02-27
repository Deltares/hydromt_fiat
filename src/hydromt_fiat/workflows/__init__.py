"""HydroMT-FIAT workflow function."""

from .aggregate import aggregate_vector_grid
from .damage import max_monetary_damage
from .exposure_geom import (
    exposure_geoms_add_columns,
    exposure_geoms_link_vulnerability,
    exposure_geoms_setup,
)
from .exposure_grid import exposure_grid_setup
from .hazard import hazard_setup
from .vulnerability import process_vulnerability_linking, vulnerability_setup

__all__ = [
    "aggregate_vector_grid",
    "exposure_geoms_add_columns",
    "exposure_geoms_link_vulnerability",
    "exposure_geoms_setup",
    "exposure_grid_setup",
    "hazard_setup",
    "max_monetary_damage",
    "process_vulnerability_linking",
    "vulnerability_setup",
]
