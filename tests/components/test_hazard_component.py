import logging

import pytest
import xarray as xr

from hydromt_fiat.components import HazardGridComponent
from hydromt_fiat.errors import MissingRegionError


def test_hazard_component_empty(mock_model):
    # Set up the component
    component = HazardGridComponent(model=mock_model)

    # Assert some very basic stuff
    assert component._filename == "hazard/hazard_grid.nc"
    assert len(component.data) == 0
    assert isinstance(component.data, xr.Dataset)


def test_hazard_component_setup_event(
    caplog,
    model,
    build_region,
):
    # Setup the component
    model.setup_region(build_region)
    component = HazardGridComponent(model=model)
    # Test hazard event
    caplog.set_level(logging.INFO)
    component.setup_hazard(hazard_fnames="flood_event")

    assert "Added flooding hazard map: flood_event" in caplog.text
    assert model.config.get_value("hazard.file") == "hazard/hazard_grid.nc"
    assert model.config.get_value("hazard.elevation_reference") == "datum"

    # Test setting data to hazard grid with data
    component.setup_hazard(hazard_fnames="flood_event_highres")
    assert model.config.get_value("hazard.settings.var_as_band")

    # Check if both ds are still there
    assert "flood_event" in component.data.data_vars.keys()
    assert "flood_event_highres" in component.data.data_vars.keys()


def test_hazard_component_setup_risk(
    model,
    build_region,
):
    # Setup the compoentn
    model.setup_region(build_region)
    component = HazardGridComponent(model=model)

    # Test hazard with return period
    component.setup_hazard(
        hazard_fnames=["flood_event_highres"],
        risk=True,
        return_periods=[50000],
    )

    assert isinstance(component.data, xr.Dataset)
    assert model.config.get_value("hazard.risk")
    assert model.config.get_value("hazard.return_periods") == [50000]


def test_hazard_component_setup_errors(model):
    # Setup the component
    component = HazardGridComponent(model=model)

    # Assert the errors
    with pytest.raises(
        ValueError, match="Cannot perform risk analysis without return periods"
    ):
        component.setup_hazard(hazard_fnames="test.nc", risk=True)

    with pytest.raises(
        ValueError, match="Return periods do not match the number of hazard files"
    ):
        component.setup_hazard(
            hazard_fnames=["test1.nc", "test2.nc"],
            risk=True,
            return_periods=[1, 2, 3],
        )

    with pytest.raises(
        MissingRegionError,
        match=("Region component is missing for setting up hazard data."),
    ):
        component.setup_hazard(hazard_fnames=["flood_event"])
