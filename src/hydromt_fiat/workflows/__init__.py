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
    infer_exposure_geom_attrs,
)
from .exposure_grid import (
    exposure_grid_categorized_setup,
    exposure_grid_category_values,
    exposure_grid_default_setup,
    exposure_grid_from_geometries,
    infer_exposure_grid_attrs,
)
from .hazard import hazard_setup, infer_hazard_attrs
from .utils import ensure_dataset, process_table
from .value import max_value, max_value_direct
from .vulnerability import (
    generate_vulnerability_identifiers,
    infer_vulnerability_attrs,
    merge_vulnerability_data,
    process_vulnerability_link,
    vulnerability_nd_from_1d,
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
    "infer_exposure_geom_attrs",
    "infer_exposure_grid_attrs",
    "infer_hazard_attrs",
    "infer_vulnerability_attrs",
    "max_value",
    "max_value_direct",
    "merge_vulnerability_data",
    "prep_data_for_aggregation",
    "process_table",
    "process_vulnerability_link",
    "vulnerability_nd_from_1d",
    "vulnerability_setup",
    "vulnerability_setup_from_v0",
]
