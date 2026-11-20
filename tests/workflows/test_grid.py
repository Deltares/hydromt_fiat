import numpy as np
import xarray as xr

from hydromt_fiat.workflows import grid_fixed_from_finite


def test_grid_fixed_from_finite(hazard: xr.Dataset):
    # Call the function
    out = grid_fixed_from_finite(hazard["flood_event"], value=5)

    # Assert the output
    assert isinstance(out, xr.DataArray)
    assert out.raster.shape == hazard.raster.shape
    assert out.dtype == np.float32
    assert out.attrs["_FillValue"] == -9999
    # Finite cells are set to the fixed value, nodata cells are left as is
    finite = hazard["flood_event"].values != hazard["flood_event"].raster.nodata
    assert finite.any()
    np.testing.assert_array_equal(out.values[finite], 5)
    np.testing.assert_array_equal(out.values[~finite], -9999)


def test_grid_fixed_from_finite_no_inplace(hazard: xr.Dataset):
    # Call the function
    out = grid_fixed_from_finite(hazard["flood_event"], value=5)

    # Assert the input data is not altered
    assert out is not hazard["flood_event"]
    assert not np.all(hazard["flood_event"].values == 5)
