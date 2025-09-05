import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
import xarray as xr
from hydromt.model import ModelRoot

from hydromt_fiat import FIATModel
from hydromt_fiat.components import HazardComponent
from hydromt_fiat.errors import MissingRegionError


def test_hazard_component_empty(
    mock_model: MagicMock,
):
    # Set up the component
    component = HazardComponent(model=mock_model)

    # Assert some very basic stuff
    assert component._filename == "hazard.nc"
    assert len(component.data) == 0
    assert isinstance(component.data, xr.Dataset)


def test_hazard_component_read(
    mock_model_config: MagicMock,
    model_cached: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_cached, mode="r"),
    )
    # Setup the component
    component = HazardComponent(model=mock_model_config)
    # Assert current state
    assert component._data is None

    # Read the data by calling 'data' property
    # This will fall back on the config
    component.data

    # Assert the state
    assert component._data is not None
    assert len(component.data.data_vars) == 1


def test_hazard_component_read_sig(
    mock_model_config: MagicMock,
    model_cached: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_cached, mode="r"),
    )
    # Setup the component
    component = HazardComponent(model=mock_model_config)

    # Read data with the 'read' method
    component.read("hazard.nc")

    # Assert the state
    assert len(component.data.data_vars) == 1


def test_hazard_component_write(
    tmp_path: Path,
    mock_model_config: MagicMock,
    hazard_data: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model_config)
    # Set data like a dummy
    component._data = hazard_data

    # Write the data
    component.write()

    # Assert the output
    assert Path(tmp_path, "hazard.nc").is_file()

    # Assert the config file
    assert component.model.config.get("hazard.file") == Path(tmp_path, "hazard.nc")


def test_hazard_component_write_sig(
    tmp_path: Path,
    mock_model_config: MagicMock,
    hazard_data: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model_config)
    # Set data like a dummy
    component._data = hazard_data

    # Write the data using the argument of the read method
    component.write("other/baz.nc")

    # Assert the output
    assert Path(tmp_path, "other", "baz.nc").is_file()

    # Assert the config file
    assert component.model.config.get("hazard.file") == Path(
        tmp_path, "other", "baz.nc"
    )


def test_hazard_component_setup_event(
    caplog: pytest.LogCaptureFixture,
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardComponent(model=model_with_region)
    # Test hazard event
    caplog.set_level(logging.INFO)
    component.setup(hazard_fnames="flood_event", elevation_reference="dem")

    assert "Added water_depth hazard map: flood_event" in caplog.text
    assert model_with_region.config.get("hazard.elevation_reference") == "dem"


def test_hazard_component_setup_multi(
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardComponent(model=model_with_region)

    # Test setting data to hazard grid with data
    component.setup(hazard_fnames=["flood_event", "flood_event_highres"])
    assert model_with_region.config.get("hazard.settings.var_as_band")

    # Check if both ds are still there
    assert "flood_event" in component.data.data_vars.keys()
    assert "flood_event_highres" in component.data.data_vars.keys()


def test_hazard_component_setup_risk(
    model_with_region: FIATModel,
):
    # Setup the compoentn
    component = HazardComponent(model=model_with_region)

    # Test hazard with return period
    component.setup(
        hazard_fnames=["flood_event_highres"],
        risk=True,
        return_periods=[50000],
    )

    assert isinstance(component.data, xr.Dataset)
    assert model_with_region.config.get("model.risk")
    assert model_with_region.config.get("hazard.return_periods") == [50000]


def test_hazard_component_setup_errors(model: FIATModel):
    # Setup the component
    component = HazardComponent(model=model)

    # Assert the errors
    with pytest.raises(
        ValueError, match="Cannot perform risk analysis without return periods"
    ):
        component.setup(hazard_fnames="test.nc", risk=True)

    with pytest.raises(
        ValueError, match="Return periods do not match the number of hazard files"
    ):
        component.setup(
            hazard_fnames=["test1.nc", "test2.nc"],
            risk=True,
            return_periods=[1, 2, 3],
        )

    with pytest.raises(
        MissingRegionError,
        match=("Region component is missing for setting up hazard data."),
    ):
        component.setup(hazard_fnames=["flood_event"])
