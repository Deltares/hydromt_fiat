"""Vector functionality."""

import math

import geopandas as gpd
from hydromt.gis import full_from_transform
from pyproj.crs import CRS

from hydromt_fiat.utils import SQUARE__ID, standard_unit

__all__ = ["create_square_vector_grid"]


def create_square_vector_grid(
    bbox: tuple[float, ...],
    crs: CRS,
    res: float,
    unit: str,
) -> gpd.GeoDataFrame:
    """Create a vector grid.

    Parameters
    ----------
    bbox : tuple[float, ...]
        The bounding box of the grid.
    crs : CRS
        The coordinate system of the vector grid, should be a projected crs.
    res : float
        The resolution of the grid. This defines both the y and x direction of the data.
    unit : str
        The unit of the resolution variable, e.g. m, ft, km etc..

    Returns
    -------
    gpd.GeoDataFrame
        The resulting vector grid.
    """
    # Convert the unit
    conversion = standard_unit(unit=unit, default="m")
    res *= conversion.magnitude

    # Get the sizes in y and x directions
    dy = bbox[3] - bbox[1]
    dx = bbox[2] - bbox[0]

    # Create a grid based on the bounding box of the results
    # and the resolution for the input
    vg: gpd.GeoDataFrame = full_from_transform(
        transform=(res, 0.0, bbox[0], 0.0, -res, bbox[3]),
        shape=(math.ceil(dy / res), math.ceil(dx / res)),
        crs=crs,
    ).raster.vector_grid()
    vg[SQUARE__ID] = range(len(vg))

    # Return the vector grid
    return vg
