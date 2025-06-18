import numpy as np
import pytest
import xarray as xr

from hydromt_fiat.workflows import hazard_grid


def test_hazard_grid_risk(hazard_event_data_highres: xr.DataArray):
    # test hazard risk
    hazard_data = {"flood_event_highres": hazard_event_data_highres}
    ds = hazard_grid(
        grid_like=None,
        hazard_data=hazard_data,
        hazard_type="flooding",
        return_periods=[50000],
        risk=True,
    )
    assert isinstance(ds, xr.Dataset)
    assert "flood_event_highres" in ds.data_vars
    da = ds.flood_event_highres
    assert ds.analysis == "risk"
    assert da.name == "flood_event_highres"
    assert da.return_period == 50000


def test_hazard_grid_event(hazard_event_data: xr.DataArray):
    # Test hazard event
    hazard_data = {"flood_event": hazard_event_data}
    ds = hazard_grid(
        grid_like=None,
        hazard_data=hazard_data,
        hazard_type="flooding",
        risk=False,
    )
    assert isinstance(ds, xr.Dataset)
    assert "flood_event" in ds.data_vars
    da = ds.flood_event
    assert ds.analysis == "event"
    assert da.name == "flood_event"
    assert "return_period" not in da.attrs.keys()


def test_hazard_grid_reproj(
    hazard_event_data: xr.DataArray,
    hazard_event_data_highres: xr.DataArray,
):
    # assert the shapes at the start
    assert hazard_event_data.shape == (5, 4)
    assert hazard_event_data_highres.shape == (94, 93)

    # Setup with a grid_like
    hazard_data = {"event": hazard_event_data_highres}
    ds = hazard_grid(
        grid_like=hazard_event_data,
        hazard_data=hazard_data,
        hazard_type="flooding",
        risk=False,
    )

    assert ds.event.name == "event"
    # More importantly, check the shape
    assert ds.event.shape == (5, 4)  # Should be the same as the hazard event data


def test_hazard_grid_unit_default(hazard_event_data: xr.DataArray):
    # Call the workflow function
    hazard_data = {"event": hazard_event_data}
    ds = hazard_grid(
        grid_like=None,
        hazard_data=hazard_data,
        hazard_type="flooding",
    )

    # Assert the avg level
    avg_level = ds.event.mean().values
    assert np.isclose(avg_level, 1.7947)


def test_hazard_grid_unit_differ(
    caplog: pytest.LogCaptureFixture,
    hazard_event_data: xr.DataArray,
):
    hazard_data = {"event": hazard_event_data}
    # Suppose it's in a different unit
    ds = hazard_grid(
        grid_like=None,
        hazard_data=hazard_data,
        hazard_type="flooding",
        unit="ft",
    )

    # Assert the avg level
    avg_level_ft = ds.event.mean().values
    assert (
        "Given unit (ft) does not match the standard unit (m) for length" in caplog.text
    )
    assert np.isclose(avg_level_ft, 0.547029)
