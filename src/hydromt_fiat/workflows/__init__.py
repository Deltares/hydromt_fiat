"""HydroMT-FIAT workflow function."""

from .aggregate import aggregate_spatially, prep_data_for_aggregation
from .exposure_geom import (
    exposure_geoms_add_columns,
    exposure_geoms_link_vulnerability,
    exposure_geoms_setup,
)
from .exposure_grid import exposure_grid_setup
from .hazard import hazard_setup
from .value import max_value, max_value_direct, process_cost_table
from .vulnerability import (
    merge_vulnerability_curves,
    merge_vulnerability_identifiers,
    process_vulnerability_link,
    vulnerability_setup,
)

__all__ = [
    "aggregate_spatially",
    "exposure_geoms_add_columns",
    "exposure_geoms_link_vulnerability",
    "exposure_geoms_setup",
    "exposure_grid_setup",
    "hazard_setup",
    "max_value",
    "max_value_direct",
    "merge_vulnerability_curves",
    "merge_vulnerability_identifiers",
    "prep_data_for_aggregation",
    "process_cost_table",
    "process_vulnerability_link",
    "vulnerability_setup",
]
