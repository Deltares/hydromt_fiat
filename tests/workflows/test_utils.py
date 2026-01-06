import logging

import pytest
import xarray as xr

from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray


def test__process_dataarray(
    hazard_event_data: xr.DataArray,
):
    # Call the function
    da = _process_dataarray(da=hazard_event_data, da_name="flood_dataarray")

    # Assert the output
    assert da.encoding["_FillValue"] is None
    assert da.name == "flood_dataarray"
    assert "grid_mapping" not in da.encoding.keys()


def test__process_dataarray_rotated(
    caplog: pytest.LogCaptureFixture,
    rotated_grid: xr.DataArray,
):
    caplog.set_level(logging.WARNING)
    # Assert rotated grid
    assert "xc" in rotated_grid.coords
    assert rotated_grid.xc.shape == (2, 2)
    # Call the function
    da = _process_dataarray(da=rotated_grid, da_name="foo")

    # Assert the output
    assert "Hazard grid is rotated." in caplog.text
    assert "xc" not in da.coords


def test__merge_dataarrays(
    caplog: pytest.LogCaptureFixture,
    hazard_event_data: xr.DataArray,
):
    caplog.set_level(logging.WARNING)
    # Small list of dataarray's
    das = [hazard_event_data, hazard_event_data]
    # Call the function
    ds = _merge_dataarrays(grid_like=None, dataarrays=das)

    # Assert the warning message and output
    warning_msg = "No known grid provided to reproject to, \
defaulting to first specified grid for transform and extent"
    assert warning_msg in caplog.text
    assert isinstance(ds, xr.Dataset)
