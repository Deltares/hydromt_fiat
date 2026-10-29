import logging

import geopandas as gpd
import numpy as np
import pytest
import xarray as xr

from hydromt_fiat.gis.raster import (
    expand_raster_to_bounds,
    merge_rasters,
    rasterize,
)


def test_expand_raster_to_bounds(
    caplog: pytest.LogCaptureFixture,
    raster: xr.DataArray,
):
    foo = raster()
    caplog.set_level(logging.INFO)
    # Assert current attibutes
    np.testing.assert_array_almost_equal(
        foo.raster.bounds,
        [0.0, 0.0, 10.0, 10.0],
        decimal=1,
    )

    # Call the function
    da = expand_raster_to_bounds(
        ds=foo,
        bbox=(-5.0, -5.0, 10.0, 20.0),  # Double the height, bit extra on the minimum
    )

    # Assert the output
    np.testing.assert_array_almost_equal(
        da.raster.bounds,
        [-5.0, -5.0, 10.0, 20.0],
        decimal=1,
    )
    assert da.shape == (25, 15)
    assert np.array_equal(da.values[10:20, 5:15], np.ones((10, 10)))
    assert np.array_equal(da.values[:10, 5:15], np.ones((10, 10)) * -9999)
    # No extrapolation so, fields with data should still be 10 by 10
    assert da.where(da == 1, drop=True).shape == (10, 10)
    assert "Checking raster extent versus region bounding box" in caplog.text
    assert "Raster smaller than the region bounding box" in caplog.text


def test_expand_raster_to_bounds_nothing(
    caplog: pytest.LogCaptureFixture,
    raster: xr.DataArray,
):
    foo = raster()
    caplog.set_level(logging.INFO)
    # Assert current attibutes
    np.testing.assert_array_almost_equal(
        foo.raster.bounds,
        [0.0, 0.0, 10.0, 10.0],
        decimal=1,
    )

    # Call the function
    da = expand_raster_to_bounds(
        ds=foo,
        bbox=(0.0, 0.0, 10.0, 10.0),  # Same extent
    )

    # Assert the output
    np.testing.assert_array_almost_equal(
        da.raster.bounds,
        foo.raster.bounds,
        decimal=1,
    )
    assert da.shape == (10, 10)
    assert "Checking raster extent versus region bounding box" in caplog.text
    assert "Raster smaller than the region bounding box" not in caplog.text


def test_merge_rasters(
    raster: xr.DataArray,
):
    # Small list of dataarray's
    das = [raster(), raster("baz")]
    # Call the function
    ds = merge_rasters(dataarrays=das)

    # Assert the warning message and output
    assert isinstance(ds, xr.Dataset)


def test_rasterize(
    exposure_vector_clipped: gpd.GeoDataFrame,
    hazard_clipped: xr.Dataset,
):
    # Call the function
    out = rasterize(
        geom=exposure_vector_clipped,
        column="max_damage_structure",
        ds_like=hazard_clipped,
    )

    # Assert the output
    assert out.raster.shape == hazard_clipped.raster.shape
    assert np.isnan(out.raster.nodata)
    np.testing.assert_almost_equal(np.nansum(out), 3.3000688e07, decimal=0)

    # Replace
    out2 = rasterize(
        geom=exposure_vector_clipped,
        column="max_damage_structure",
        ds_like=hazard_clipped,
        method="replace",
    )

    # Assert the output
    assert out2.raster.shape == hazard_clipped.raster.shape
    assert np.isnan(out2.raster.nodata)
    np.testing.assert_almost_equal(
        np.nansum(out2),
        2.7837082e07,  # Lower ofcourse
        decimal=0,
    )
    assert np.nansum(out2) < np.nansum(out)


def test_rasterize_errors(exposure_vector_clipped: gpd.GeoDataFrame):
    # Call the function with a nonsense column
    with pytest.raises(
        ValueError, match="'foo' column not found in exposure geometry data"
    ):
        _ = rasterize(
            geom=exposure_vector_clipped,
            column="foo",
            ds_like=None,
        )
