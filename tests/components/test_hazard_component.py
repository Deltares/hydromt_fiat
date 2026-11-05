import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
import xarray as xr
from hydromt.model import ModelRoot
from hydromt.model.mode import ModelMode
from pytest_mock import MockerFixture

from hydromt_fiat import FIATModel
from hydromt_fiat.components import HazardComponent
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.settings.hazard import HazardVariable
from hydromt_fiat.utils import (
    HAZARD,
    RP,
    WATER__DEPTH,
)


def test_hazard_component_empty(
    mock_model: MagicMock,
):
    # Set up the component
    component = HazardComponent(model=mock_model("geom"))

    # Assert some very basic stuff
    assert component._filename == f"{HAZARD}.nc"
    assert len(component.data) == 0
    assert isinstance(component.data, xr.Dataset)


def test_hazard_component_read(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    # Setup the model
    model = mock_model_config("geom")
    type(model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Setup the component
    component = HazardComponent(model=model)
    # Assert current state
    assert component._data is None

    # Read the data by calling 'data' property
    # This will fall back on the config
    component.data

    # Assert the state
    assert component._data is not None
    assert len(component.data.data_vars) == 1
    # Assert the attributes, which are inferred as there are no settings present
    assert component.data_attrs["flood_event"].type == WATER__DEPTH


def test_hazard_component_read_settings(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    # Setup the model with the settings file
    model = mock_model_config("geom")
    type(model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    model.config.read("settings_geom.toml")
    # Set a different type in the settings
    model.config.data.hazard.variables[0].type = "duration"
    # Setup the component
    component = HazardComponent(model=model)

    # Read the data by calling 'data' property
    component.data

    # Assert the attributes, which are taken from the settings
    assert component.data_attrs["flood_event"].type == "duration"


def test_hazard_component_read_sig(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    # Setup the model
    model = mock_model_config("geom")
    type(model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Setup the component
    component = HazardComponent(model=model)

    # Read data with the 'read' method
    component.read(f"{HAZARD}.nc")

    # Assert the state
    assert len(component.data.data_vars) == 1


def test_hazard_component_read_nothing(
    mocker: MockerFixture,
    mock_model_config: MagicMock,
):
    # Setup the model
    model = mock_model_config("geom")
    mocker.patch.object(
        type(model.root),
        "mode",
        new_callable=PropertyMock,
        return_value=ModelMode("r"),
    )
    # Setup the component
    component = HazardComponent(model=model)
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
    component = HazardComponent(model=mock_model_config("geom"))
    # Set data like a dummy
    component._data = hazard_clipped
    component._data_attrs = {}
    component.set_attrs("flood_event", dict(type=WATER__DEPTH))

    # Write the data
    component.write()

    # Assert the output
    assert Path(tmp_path, f"{HAZARD}.nc").is_file()

    # Assert the config file
    assert component.model.config.data.hazard.file == Path(tmp_path, f"{HAZARD}.nc")
    variables = component.model.config.data.hazard.variables
    assert len(variables) == 1
    assert variables[0].name == "flood_event"
    assert variables[0].type == WATER__DEPTH


def test_hazard_component_write_sig(
    tmp_path: Path,
    mock_model_config: MagicMock,
    hazard_clipped: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model_config("geom"))
    # Set data like a dummy
    component._data = hazard_clipped
    component._data["flood_event2"] = hazard_clipped["flood_event"]
    component._data_attrs = {}
    component.set_attrs("flood_event", dict(type=WATER__DEPTH))
    component.set_attrs("flood_event2", dict(type=WATER__DEPTH))

    # Write the data using the argument of the read method
    component.write("other/baz.nc")

    # Assert the output
    assert Path(tmp_path, "other", "baz.nc").is_file()

    # Assert the config file
    assert component.model.config.data.hazard.file == Path(tmp_path, "other", "baz.nc")
    assert len(component.model.config.data.hazard.variables) == 2


def test_hazard_component_create(
    caplog: pytest.LogCaptureFixture,
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardComponent(model=model_with_region)
    # Test hazard event
    caplog.set_level(logging.INFO)
    component.create(hazard_fnames="flood_event")

    assert "Processing water_depth hazard data" in caplog.text
    assert "flood_event" in component.data.data_vars
    assert component.data.raster.shape == (7, 6)
    # Assert the attributes
    assert isinstance(component.data_attrs["flood_event"], HazardVariable)
    assert component.data_attrs["flood_event"].type == WATER__DEPTH
    assert component.data_attrs["flood_event"].rp is None


def test_hazard_component_create_multi(
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardComponent(model=model_with_region)

    # Test setting data to hazard grid with data
    component.create(hazard_fnames=["flood_event", "flood_event_highres"], expand=False)

    # Check if both ds are still there
    assert "flood_event" in component.data.data_vars
    assert "flood_event_highres" in component.data.data_vars
    assert set(component.data_attrs) == {"flood_event", "flood_event_highres"}


def test_hazard_component_create_risk(
    model: FIATModel,
):
    # Setup the compoentn
    component = HazardComponent(model=model)

    # Test hazard with return period
    component.create(
        hazard_fnames=["flood_event_highres"],
        risk=True,
        return_periods=[50000],
        region=False,
    )

    assert isinstance(component.data, xr.Dataset)
    assert component.data.flood_event_highres.attrs[RP] == 50000
    assert model.config.data.risk
    # Assert the attributes
    assert component.data_attrs["flood_event_highres"].rp == 50000


def test_hazard_component_create_errors(model: FIATModel):
    # Setup the component
    component = HazardComponent(model=model)

    # Assert the errors
    with pytest.raises(
        ValueError, match="Cannot perform risk analysis without return periods"
    ):
        component.create(hazard_fnames="test.nc", risk=True)

    with pytest.raises(
        ValueError, match="Return periods do not match the number of hazard files"
    ):
        component.create(
            hazard_fnames=["test1.nc", "test2.nc"],
            risk=True,
            return_periods=[1, 2, 3],
        )

    with pytest.raises(
        MissingRegionError,
        match=("Region component is missing for setting up hazard data"),
    ):
        component.create(hazard_fnames=["flood_event"])
