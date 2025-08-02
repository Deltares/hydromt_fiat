import logging

import pandas as pd
import pytest
import xarray as xr

from hydromt_fiat.workflows import exposure_grid


def test_exposure_grid(
    exposure_grid_data_ind: xr.DataArray,
    exposure_grid_link: pd.DataFrame,
):
    # Call the function
    ds = exposure_grid(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        exposure_linking=exposure_grid_link,
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert ds.industrial_content.attrs.get("fn_damage") == "in1"


def test_exposure_grid_no_linking(
    caplog: pytest.LogCaptureFixture,
    exposure_grid_data_ind: xr.DataArray,
    exposure_grid_link: pd.DataFrame,
):
    caplog.set_level(logging.WARNING)
    # Call the function
    ds = exposure_grid(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        exposure_linking=exposure_grid_link.replace("industrial_content", "unknown"),
    )

    # Assert the logging message
    log_msg = (
        "Exposure file name, 'industrial_content', not found in linking table."
        " Setting damage curve name attribute to 'industrial_content'."
    )
    assert log_msg in caplog.text

    # Check if damage function defaults to exposure file name
    assert ds.industrial_content.attrs.get("fn_damage") == "industrial_content"


def test_exposure_grid_errors(
    exposure_grid_data_ind: xr.DataArray,
):
    # Assert an error on the missing necessary columns
    with pytest.raises(
        ValueError,
        match="Missing column, 'exposure_link' in exposure grid linking table",
    ):
        # Call the function
        _ = exposure_grid(
            grid_like=None,
            exposure_data={"industrial_content": exposure_grid_data_ind},
            exposure_linking=pd.DataFrame(),
        )
