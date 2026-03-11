import logging

import numpy as np
import pytest
import xarray as xr

from hydromt_fiat.gis.raster import expand_raster_to_bounds


def test_expand_raster_to_bounds(
    caplog: pytest.LogCaptureFixture,
    raster: xr.DataArray,
):
    caplog.set_level(logging.INFO)
    # Assert current attibutes
    np.testing.assert_array_almost_equal(
        raster.raster.bounds,
        [0.0, 0.0, 10.0, 10.0],
        decimal=1,
    )

    # Call the function
    da = expand_raster_to_bounds(
        ds=raster,
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
    caplog.set_level(logging.INFO)
    # Assert current attibutes
    np.testing.assert_array_almost_equal(
        raster.raster.bounds,
        [0.0, 0.0, 10.0, 10.0],
        decimal=1,
    )

    # Call the function
    da = expand_raster_to_bounds(
        ds=raster,
        bbox=(0.0, 0.0, 10.0, 10.0),  # Same extent
    )

    # Assert the output
    np.testing.assert_array_almost_equal(
        da.raster.bounds,
        raster.raster.bounds,
        decimal=1,
    )
    assert da.shape == (10, 10)
    assert "Checking raster extent versus region bounding box" in caplog.text
    assert "Raster smaller than the region bounding box" not in caplog.text
