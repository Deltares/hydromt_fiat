import numpy as np
import xarray as xr

from hydromt_fiat.gis.raster_utils import cell_size, check_spatial, force_ns


def test_cell_size(hazard_clipped: xr.Dataset):
    # Call the function
    size = cell_size(hazard_clipped)

    # Assert the output
    np.testing.assert_almost_equal(size, 10000, decimal=0)


def test_cell_size_geographic(hazard_clipped: xr.Dataset):
    # Call the function and needing to calculate the transform
    size = cell_size(hazard_clipped.raster.reproject(dst_crs=4326))

    # Assert the output
    np.testing.assert_almost_equal(size, 9239, decimal=0)


def test_check_spatial(hazard_clipped: xr.Dataset):
    # Call the function
    flag = check_spatial(hazard_clipped)

    # Assert the output
    assert flag


def test_check_spatial_false():
    # Call the function
    flag = check_spatial(xr.Dataset())

    # Assert the output
    assert not flag


def test_force_ns(ns_raster: xr.DataArray):
    # Call the function
    da = force_ns(ns_raster)

    # Assert the output
    assert da.raster.res[1] < 1
    assert da.raster.res[1] == ns_raster.raster.res[1]  # Nothing happened


def test_force_ns_flip(ns_raster: xr.DataArray):
    # Flip the raster to make sure the function works
    raster = ns_raster.raster.flipud()
    assert raster.raster.res[1] > 0
    # Call the function
    da = force_ns(raster)

    # Assert the output
    assert da.raster.res[1] < 1
    assert da.raster.res[1] != raster.raster.res[1]  # It got flipped
