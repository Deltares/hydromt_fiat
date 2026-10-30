"""HydroMT-FIAT workflow function."""

from .aggregate import (
    aggregate_geom_spatially,
    aggregate_grid,
    prep_data_for_aggregation,
)
from .exposure_geom import (
    exposure_geoms_add_columns,
    exposure_geoms_link_vulnerability,
    exposure_geoms_setup,
)
from .exposure_grid import (
    exposure_grid_categorized_setup,
    exposure_grid_category_values,
    exposure_grid_default_setup,
    exposure_grid_from_geometries,
)
from .hazard import hazard_setup
from .utils import ensure_dataset, process_table
from .value import max_value, max_value_direct
from .vulnerability import (
    generate_vulnerability_identifiers,
    merge_vulnerability_curves,
    process_vulnerability_link,
    vulnerability_setup,
    vulnerability_setup_from_v0,
)

__all__ = [
    "aggregate_geom_spatially",
    "aggregate_grid",
    "ensure_dataset",
    "exposure_geoms_add_columns",
    "exposure_geoms_link_vulnerability",
    "exposure_geoms_setup",
    "exposure_grid_categorized_setup",
    "exposure_grid_category_values",
    "exposure_grid_default_setup",
    "exposure_grid_from_geometries",
    "generate_vulnerability_identifiers",
    "hazard_setup",
    "max_value",
    "max_value_direct",
    "merge_vulnerability_curves",
    "prep_data_for_aggregation",
    "process_table",
    "process_vulnerability_link",
    "vulnerability_setup",
    "vulnerability_setup_from_v0",
]
