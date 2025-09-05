import logging

import pandas as pd
import pytest
import xarray as xr

from hydromt_fiat.workflows import exposure_grid_setup


def test_exposure_grid_setup(
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_linking: pd.DataFrame,
):
    # Call the function
    ds = exposure_grid_setup(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        vulnerability=vulnerability_linking,
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert len(ds.data_vars) == 1
    assert ds.industrial_content.attrs.get("fn_damage") == "in2"


def test_exposure_grid_setup_linking(
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_linking: pd.DataFrame,
    exposure_grid_link: pd.DataFrame,
):
    # Call the function, bit stupid is this table just returns the same
    ds = exposure_grid_setup(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        vulnerability=vulnerability_linking,
        exposure_linking=exposure_grid_link,
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert ds.industrial_content.attrs.get("fn_damage") == "in2"


def test_exposure_grid_setup_link_no(
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_linking: pd.DataFrame,
):
    # Call the function, bit stupid is this table just returns the same
    ds = exposure_grid_setup(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        vulnerability=vulnerability_linking,
        exposure_linking=pd.DataFrame(data={"exposure_link": [], "object_type": []}),
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert ds.industrial_content.attrs.get("fn_damage") == "in2"


def test_exposure_grid_setup_alt(
    caplog: pytest.LogCaptureFixture,
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_linking_alt: pd.DataFrame,
):
    caplog.set_level(logging.WARNING)
    # Call the function, shouldn't be able to link to the vulnerability
    ds = exposure_grid_setup(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        vulnerability=vulnerability_linking_alt,
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert len(ds.data_vars) == 0
    # Assert the logging
    assert "Couldn't link 'industrial_content' to vulnerability, skipping..."


def test_exposure_grid_setup_alt_link(
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_linking_alt: pd.DataFrame,
):
    # Call the function, shouldn't be able to link to the vulnerability
    ds = exposure_grid_setup(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        vulnerability=vulnerability_linking_alt,
        exposure_linking=pd.DataFrame(
            data={
                "exposure_link": ["industrial_content"],
                "object_type": ["industrial"],
            }
        ),
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert len(ds.data_vars) == 1


def test_exposure_grid_setup_errors(
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_linking: pd.DataFrame,
):
    # Assert an error on the missing necessary columns
    with pytest.raises(
        ValueError,
        match="Missing column, 'exposure_link' in exposure grid linking table",
    ):
        # Call the function
        _ = exposure_grid_setup(
            grid_like=None,
            exposure_data={"industrial_content": exposure_grid_data_ind},
            vulnerability=vulnerability_linking,
            exposure_linking=pd.DataFrame(),
        )
