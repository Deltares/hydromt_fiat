"""GIS submodule."""

from .raster import expand_raster_to_bounds
from .vector import create_square_vector_grid

__all__ = [
    "create_square_vector_grid",
    "expand_raster_to_bounds",
]
