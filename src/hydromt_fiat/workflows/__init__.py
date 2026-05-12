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
from .vulnerability import (
    build_vulnerability_link,
    merge_curves,
    use_curve_names,
    vulnerability_setup,
)

__all__ = [
    "aggregate_vector_grid",
    "build_vulnerability_link",
    "exposure_geoms_add_columns",
    "exposure_geoms_link_vulnerability",
    "exposure_geoms_setup",
    "exposure_grid_setup",
    "hazard_setup",
    "max_monetary_damage",
    "merge_curves",
    "use_curve_names",
    "vulnerability_setup",
]
