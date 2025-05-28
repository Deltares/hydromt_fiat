import logging
from unittest.mock import MagicMock

import pytest
import xarray as xr

from hydromt_fiat import FIATModel
from hydromt_fiat.components import HazardGridComponent
from hydromt_fiat.errors import MissingRegionError


def test_hazard_component_empty(
    mock_model: MagicMock,
):
    # Set up the component
    component = HazardGridComponent(model=mock_model)

    # Assert some very basic stuff
    assert component._filename == "hazard/hazard_grid.nc"
    assert len(component.data) == 0
    assert isinstance(component.data, xr.Dataset)


def test_hazard_component_setup_event(
    caplog: pytest.LogCaptureFixture,
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardGridComponent(model=model_with_region)
    # Test hazard event
    caplog.set_level(logging.INFO)
    component.setup_hazard(hazard_fnames="flood_event", elevation_reference="dem")

    assert "Added water_depth hazard map: flood_event" in caplog.text
    assert model_with_region.config.get_value("hazard.file") == "hazard/hazard_grid.nc"
    assert model_with_region.config.get_value("hazard.elevation_reference") == "dem"

    # Test setting data to hazard grid with data
    component.setup_hazard(hazard_fnames="flood_event_highres")
    assert model_with_region.config.get_value("hazard.settings.var_as_band")

    # Check if both ds are still there
    assert "flood_event" in component.data.data_vars.keys()
    assert "flood_event_highres" in component.data.data_vars.keys()


def test_hazard_component_setup_risk(
    model_with_region: FIATModel,
):
    # Setup the compoentn
    component = HazardGridComponent(model=model_with_region)

    # Test hazard with return period
    component.setup_hazard(
        hazard_fnames=["flood_event_highres"],
        risk=True,
        return_periods=[50000],
    )

    assert isinstance(component.data, xr.Dataset)
    assert model_with_region.config.get_value("model.risk")
    assert model_with_region.config.get_value("hazard.return_periods") == [50000]


def test_hazard_component_setup_errors(model: FIATModel):
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
