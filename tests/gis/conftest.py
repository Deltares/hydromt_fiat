import numpy as np
import pytest
import xarray as xr


@pytest.fixture
def simple_raster() -> xr.DataArray:
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
