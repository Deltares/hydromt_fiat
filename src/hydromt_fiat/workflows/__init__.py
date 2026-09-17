"""HydroMT-FIAT workflow function."""

from .aggregate import aggregate_spatially, prep_data_for_aggregation
from .exposure_geom import (
    exposure_geoms_add_columns,
    exposure_geoms_link_vulnerability,
    exposure_geoms_setup,
)
from .exposure_grid import (
    exposure_grid_categorized_setup,
    exposure_grid_category_values,
    exposure_grid_default_setup,
)
from .hazard import hazard_setup
from .utils import process_table
from .value import max_value, max_value_direct
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
    "exposure_grid_categorized_setup",
    "exposure_grid_category_values",
    "exposure_grid_default_setup",
    "hazard_setup",
    "max_value",
    "max_value_direct",
    "merge_vulnerability_curves",
    "merge_vulnerability_identifiers",
    "prep_data_for_aggregation",
    "process_table",
    "process_vulnerability_link",
    "vulnerability_setup",
]
