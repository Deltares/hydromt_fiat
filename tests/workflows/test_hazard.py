import numpy as np
import pytest
import xarray as xr

from hydromt_fiat.settings.hazard import Hazard
from hydromt_fiat.utils import EVENT, RISK, RP, TYPE, WATER__DEPTH
from hydromt_fiat.workflows import hazard_setup, infer_hazard_attrs


def test_hazard_setup_risk(hazard_event_data_highres: xr.DataArray):
    # test hazard risk
    hazard_data = {"flood_event_highres": hazard_event_data_highres}
    ds, attrs = hazard_setup(
        grid_like=None,
        hazard_data=hazard_data,
        hazard_type="flooding",
        return_periods=[50000],
        risk=True,
    )
    assert isinstance(ds, xr.Dataset)
    assert "flood_event_highres" in ds.data_vars
    da = ds.flood_event_highres
    assert ds.analysis == RISK
    assert da.name == "flood_event_highres"
    assert da.rp == 50000
    # Assert the data attributes
    assert attrs == {"flood_event_highres": {TYPE: "flooding", RP: 50000}}


def test_hazard_setup_event(hazard_event_data: xr.DataArray):
    # Test hazard event
    hazard_data = {"flood_event": hazard_event_data}
    ds, attrs = hazard_setup(
        grid_like=None,
        hazard_data=hazard_data,
        hazard_type="flooding",
        risk=False,
    )
    assert isinstance(ds, xr.Dataset)
    assert "flood_event" in ds.data_vars
    da = ds.flood_event
    assert ds.analysis == EVENT
    assert da.name == "flood_event"
    assert "rp" not in da.attrs.keys()
    # Assert the data attributes
    assert attrs == {"flood_event": {TYPE: "flooding"}}


def test_hazard_setup_reproj(
    hazard_event_data: xr.DataArray,
    hazard_event_data_highres: xr.DataArray,
):
    # assert the shapes at the start
    assert hazard_event_data.shape == (5, 4)
    assert hazard_event_data_highres.shape == (94, 93)

    # Setup with a grid_like
    hazard_data = {"event": hazard_event_data_highres}
    ds, _ = hazard_setup(
        grid_like=hazard_event_data,
        hazard_data=hazard_data,
        hazard_type="flooding",
        risk=False,
    )

    assert ds.event.name == "event"
    # More importantly, check the shape
    assert ds.event.shape == (5, 4)  # Should be the same as the hazard event data


def test_hazard_setup_unit_default(hazard_event_data: xr.DataArray):
    # Call the workflow function
    hazard_data = {"event": hazard_event_data}
    ds, _ = hazard_setup(
        grid_like=None,
        hazard_data=hazard_data,
        hazard_type="flooding",
    )

    # Assert the avg level
    avg_level = ds.event.mean().values
    assert np.isclose(avg_level, 1.7947)


def test_hazard_setup_unit_differ(
    caplog: pytest.LogCaptureFixture,
    hazard_event_data: xr.DataArray,
):
    hazard_data = {"event": hazard_event_data}
    # Suppose it's in a different unit
    ds, _ = hazard_setup(
        grid_like=None,
        hazard_data=hazard_data,
        hazard_type="flooding",
        unit="ft",
    )

    # Assert the avg level
    avg_level_ft = ds.event.mean().values
    assert (
        "Given unit (foot) does not match the standard/ default unit \
(meter) for [length]"
        in caplog.text
    )
    assert np.isclose(avg_level_ft, 0.547029)


def test_infer_hazard_attrs(hazard: xr.Dataset):
    # Call the function
    attrs = infer_hazard_attrs(hazard)

    # Assert the output, every variable defaults to water depth
    assert set(attrs) == set(hazard.data_vars)
    assert attrs["flood_event"] == {TYPE: WATER__DEPTH}


def test_infer_hazard_attrs_settings(hazard: xr.Dataset):
    # Setup the settings with an entry for a variable in the data and one that is not
    settings = Hazard(
        file="foo.nc",
        variables=[
            dict(name="flood_event", type="duration", rp=10),
            dict(name="foo", type="duration"),
        ],
    )

    # Call the function
    attrs = infer_hazard_attrs(hazard, settings=settings)

    # Assert the output, the settings take precedence over the inferred
    assert attrs["flood_event"] == {"name": "flood_event", "type": "duration", "rp": 10}
    # Nothing is added for what is not in the data
    assert "foo" not in attrs
