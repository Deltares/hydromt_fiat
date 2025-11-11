"""Raster workflows."""

import logging

import geopandas as gpd
import xarray as xr
from affine import Affine
from hydromt.gis import full_from_transform, full_like

__all__ = ["rasterize"]

logging.getLogger(f"hydromt.{__name__}")

_methods = ["point"]


def _point_to_grid():
    pass


def _acquire_grid(
    grid: xr.DataArray | None = None,
    ds_like: xr.Dataset | xr.DataArray | None = None,
    transform: Affine | None = None,
    shape: tuple | None = None,
) -> xr.DataArray:
    """Determine the grid the rasterize the vector data in."""
    if grid is not None:
        return grid
    if ds_like is not None:
        grid = full_like(other=ds_like, nodata=-9999, lazy=True)
    elif transform is not None and shape is not None:
        grid = full_from_transform(
            transform=transform,
            shape=shape,
        )


def rasterize(
    geom: gpd.GeoDataFrame,
    method: str = "point",
    grid: xr.DataArray | None = None,
    ds_like: xr.Dataset | xr.DataArray | None = None,
    transform: Affine | None = None,
    width: int | None = None,
    height: int | None = None,
) -> xr.DataArray:
    """_summary_.

    Parameters
    ----------
    geom : gpd.GeoDataFrame
        _description_
    method : str, optional
        _description_, by default "point"
    grid : xr.DataArray | None, optional
        _description_, by default None
    ds_like : xr.Dataset | xr.DataArray | None, optional
        _description_, by default None
    transform : Affine | None, optional
        _description_, by default None
    width : int | None, optional
        _description_, by default None
    height : int | None, optional
        _description_, by default None

    Returns
    -------
    xr.DataArray
        _description_
    """
    if method not in _methods:
        raise ValueError("Unknown method for rasterization")

    pass
