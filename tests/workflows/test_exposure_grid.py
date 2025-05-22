import logging

import pandas as pd
import pytest
import xarray as xr

from hydromt_fiat.workflows import exposure_grid_data


def test_exposure_grid_data(
    hazard_event_data: xr.DataArray,
):
    linking_table = pd.DataFrame(
        data=[{"type": "flood_event", "curve_id": "damage_function_file"}]
    )
    exposure_data = {"flood_event": hazard_event_data}
    ds = exposure_grid_data(
        grid_like=None,
        exposure_data=exposure_data,
        exposure_linking=linking_table,
    )
    assert isinstance(ds, xr.Dataset)
    assert ds.flood_event.attrs.get("fn_damage") == "damage_function_file"


def test_exposure_grid_data_no_linking_table_match(
    caplog: pytest.LogCaptureFixture,
    hazard_event_data: xr.DataArray,
):
    # Test without matching exposure file name in linking table
    exposure_data = {"flood_event": hazard_event_data}
    caplog.set_level(logging.WARNING)
    linking_table = pd.DataFrame(
        data=[{"type": "event", "curve_id": "damage_function_file"}]
    )

    ds = exposure_grid_data(
        grid_like=None, exposure_data=exposure_data, exposure_linking=linking_table
    )
    log_msg = (
        "Exposure file name, 'flood_event', not found in linking table."
        " Setting damage curve name attribute to 'flood_event'."
    )
    assert log_msg in caplog.text

    # Check if damage function defaults to exposure file name
    assert ds.flood_event.attrs.get("fn_damage") == "flood_event"
