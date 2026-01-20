import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
import xarray as xr
from hydromt.model import ModelRoot

from hydromt_fiat import FIATModel
from hydromt_fiat.components import HazardComponent
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.utils import (
    HAZARD,
    HAZARD_FILE,
    HAZARD_RP,
    HAZARD_SETTINGS,
    MODEL_RISK,
    VAR_AS_BAND,
)


def test_hazard_component_empty(
    mock_model: MagicMock,
):
    # Set up the component
    component = HazardComponent(model=mock_model)

    # Assert some very basic stuff
    assert component._filename == f"{HAZARD}.nc"
    assert len(component.data) == 0
    assert isinstance(component.data, xr.Dataset)


def test_hazard_component_read(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
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
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Setup the component
    component = HazardComponent(model=mock_model_config)

    # Read data with the 'read' method
    component.read(f"{HAZARD}.nc")

    # Assert the state
    assert len(component.data.data_vars) == 1


def test_hazard_component_read_nothing(
    tmp_path: Path,
    mock_model_config: MagicMock,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(tmp_path, mode="r"),
    )
    # Setup the component
    component = HazardComponent(model=mock_model_config)
    # Assert current state
    assert len(component.data) == 0

    # Read the data (nothing)
    component.read()
    # Assert still no data
    assert len(component.data) == 0


def test_hazard_component_write(
    tmp_path: Path,
    mock_model_config: MagicMock,
    hazard_clipped: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model_config)
    # Set data like a dummy
    component._data = hazard_clipped

    # Write the data
    component.write()

    # Assert the output
    assert Path(tmp_path, f"{HAZARD}.nc").is_file()

    # Assert the config file
    assert component.model.config.get(HAZARD_FILE) == Path(tmp_path, f"{HAZARD}.nc")
    assert not component.model.config.get(f"{HAZARD_SETTINGS}.{VAR_AS_BAND}")


def test_hazard_component_write_sig(
    tmp_path: Path,
    mock_model_config: MagicMock,
    hazard_clipped: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model_config)
    # Set data like a dummy
    component._data = hazard_clipped
    component._data["flood_event2"] = hazard_clipped["flood_event"]

    # Write the data using the argument of the read method
    component.write("other/baz.nc")

    # Assert the output
    assert Path(tmp_path, "other", "baz.nc").is_file()

    # Assert the config file
    assert component.model.config.get(HAZARD_FILE) == Path(tmp_path, "other", "baz.nc")
    assert component.model.config.get(f"{HAZARD_SETTINGS}.{VAR_AS_BAND}")


def test_hazard_component_setup(
    caplog: pytest.LogCaptureFixture,
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardComponent(model=model_with_region)
    # Test hazard event
    caplog.set_level(logging.INFO)
    component.setup(hazard_fnames="flood_event")

    assert "Added water_depth hazard map: flood_event" in caplog.text
    assert "flood_event" in component.data.data_vars


def test_hazard_component_setup_multi(
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardComponent(model=model_with_region)

    # Test setting data to hazard grid with data
    component.setup(hazard_fnames=["flood_event", "flood_event_highres"])

    # Check if both ds are still there
    assert "flood_event" in component.data.data_vars
    assert "flood_event_highres" in component.data.data_vars


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
    assert model_with_region.config.get(MODEL_RISK)
    assert model_with_region.config.get(HAZARD_RP) == [50000]


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
