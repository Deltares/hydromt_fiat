import xarray as xr

from hydromt_fiat.gis.raster_utils import force_ns


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
