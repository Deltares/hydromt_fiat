import numpy as np
import pytest
import xarray as xr


@pytest.fixture
def ns_raster() -> xr.DataArray:
    da = xr.DataArray(
        data=np.ones((8, 8)),
        coords={
            "y": list(range(7, -1, -1)),
            "x": list(range(0, 8, 1)),
        },
        dims=("y", "x"),
    )
    da.raster.set_crs(4326)
    return da


@pytest.fixture
def raster() -> xr.DataArray:
    da = xr.DataArray(
        data=np.ones((10, 10)),
        coords={
            "y": np.arange(9.5, 0.0, -1),
            "x": np.arange(0.5, 10.0, 1),
        },
        dims=("y", "x"),
    )
    da.raster.set_crs(4326)
    da.raster.set_nodata(-9999)
    return da
