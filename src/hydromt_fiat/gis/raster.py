"""Raster methods."""

import logging

import geopandas as gpd
import xarray as xr
from rasterio.enums import MergeAlg

__all__ = ["rasterize"]

logging.getLogger(f"hydromt.{__name__}")

_methods = ["add", "replace"]


def _point_to_grid():
    pass


def rasterize(
    gdf: gpd.GeoDataFrame,
    grid: xr.DataArray,
    column: str,
    method: str = "replace",
    all_touched: bool = True,
    weighted: bool = False,
) -> xr.DataArray:
    """_summary_.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        _description_
    grid : xr.DataArray, optional
        _description_, by default None
    column : str,
        Which column to rasterize. Should either be an integer or float based column.
    method : str, optional
        _description_, by default "replace"
    all_touched : bool, optional
        ...
    weighted : bool, optional
        ...

    Returns
    -------
    xr.DataArray
        _description_
    """
    # Quick method check
    if method not in _methods:
        raise ValueError("Unknown method for rasterization")
    if column not in gdf.columns:
        raise ValueError(f"Column '{column}' not found in geom")

    if not weighted:
        grid = grid.raster.rasterize(
            gdf=gdf,
            col_name=column,
            nodata=None,
            all_touched=all_touched,
            merge_alg=MergeAlg[method],
        )
        return grid

    vgrid = grid.raster.vector_grid(geom_type="polygon")

    return vgrid
