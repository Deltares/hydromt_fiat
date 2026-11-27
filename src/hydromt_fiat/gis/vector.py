"""Vector functionality."""

import math

import geopandas as gpd
import xarray as xr
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


def vectorize(
    data: xr.DataArray,
    buffer: float = 0.05,
    uniform: bool = True,
) -> gpd.GeoDataFrame:
    """Vectorize grid data.

    Parameters
    ----------
    data : xr.DataArray
        The gridded data.
    buffer : float, optional
        The buffer multiplier for the longest axis of the data bounds.
        The total buffer amount used is the longest axis length times this multiplier.
        The newly vectorized data is buffered and debuffered by that number to iron out
        the rough edges of the grid cells and potentially fill up some holes.
        By default 0.05.
    uniform : bool, optional
        Whether to respect the values of the data or try to vectorize all nodata values
        into one polygon (or one multipolygon), by default True.

    Returns
    -------
    gpd.GeoDataFrame
        The resulting vector data.
    """
    # Get some metadata like the bounds
    xmin, ymin, xmax, ymax = data.raster.bounds
    # Get the longest axis
    dist = max((xmax - xmin), (ymax - ymin))
    # Buffer distance is the buffer multiplier multiplied by this distance
    buffer = dist * buffer
    area = data
    # Set all nodata values to one, which helps it being vectorized into one polygon
    if uniform:
        area = data.where(data == data.raster.nodata, 1)

    # Vectorize it with hydromt
    geom = area.raster.mask_nodata().raster.vectorize()
    # Buffer and de-buffer it to fill gaps and take away rough edges
    geom = geom.buffer(buffer).buffer(-buffer)
    # Return the geometry
    return gpd.GeoDataFrame(geometry=geom, crs=data.raster.crs).reset_index(drop=True)
