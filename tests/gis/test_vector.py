import math

import geopandas as gpd
import numpy as np
import xarray as xr

from hydromt_fiat.gis import create_square_vector_grid
from hydromt_fiat.gis.vector import vectorize
from hydromt_fiat.utils import SQUARE__ID


def test_create_square_vector_grid(
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Call the function
    bbox = exposure_vector_clipped.total_bounds
    vg = create_square_vector_grid(
        bbox=bbox,
        crs=exposure_vector_clipped.crs,
        res=0.1,
        unit="km",
    )

    # Assert the output properties
    assert vg.crs.to_epsg() == exposure_vector_clipped.crs.to_epsg()
    assert (
        len(vg)
        == (math.ceil((bbox[2] - bbox[0]) / 100) * math.ceil((bbox[3] - bbox[1]) / 100))
        == 20
    )
    assert SQUARE__ID in vg.columns
    np.testing.assert_array_equal(vg[SQUARE__ID], range(0, 20))


def test_create_square_vector_grid_unit(
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Call the function
    bbox = exposure_vector_clipped.total_bounds
    vg = create_square_vector_grid(
        bbox=bbox,
        crs=exposure_vector_clipped.crs,
        res=0.1,
        unit="mile",
    )

    # Assert the output properties
    assert (
        len(vg)
        == (
            math.ceil((bbox[2] - bbox[0]) / (100 * 1.6))
            * math.ceil((bbox[3] - bbox[1]) / (100 * 1.6))
        )
        == 9
    )


def test_vectorize(
    raster: xr.DataArray,
):
    # Call the function
    da = raster()
    geom = vectorize(da)

    # Assert the output
    assert len(geom) == 1
    assert geom.crs.to_epsg() == 4326
    np.testing.assert_almost_equal(geom.geometry.iloc[0].area, 100, decimal=3)
    np.testing.assert_array_equal(geom.total_bounds, da.raster.bounds)


def test_vectorize_buffer(
    raster: xr.DataArray,
):
    # Setup the data with a hole (nodata) in the middle
    da = raster()
    da[4:6, 4:6] = da.raster.nodata

    # Call the function without a buffer
    geom = vectorize(da, buffer=0)
    # Assert the hole is present
    assert geom.geometry.iloc[0].area == 96

    # Call the function with a buffer larger than the hole
    geom = vectorize(da, buffer=0.1)
    # Assert the hole is filled, only the corners are rounded off
    assert len(geom) == 1
    assert geom.geometry.iloc[0].area > 99


def test_vectorize_uniform(
    raster: xr.DataArray,
):
    # Setup the data with two different values
    da = raster()
    da[:, 5:] = 2

    # Call the function
    geom = vectorize(da, buffer=0)
    # Assert the values are ignored, i.e. one polygon
    assert len(geom) == 1
    assert geom.geometry.iloc[0].area == 100

    # Call the function while respecting the values
    geom = vectorize(da, buffer=0, uniform=False)
    # Assert a polygon per value
    assert len(geom) == 2
    assert geom.geometry.area.tolist() == [50, 50]
