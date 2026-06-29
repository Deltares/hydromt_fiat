import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, PropertyMock

import pytest
from hydromt.model import ModelRoot
from hydromt.model.mode import ModelMode
from hydromt.readers import read_toml
from pytest_mock import MockerFixture

from hydromt_fiat.components import ConfigComponent
from hydromt_fiat.settings import Settings
from hydromt_fiat.utils import (
    GEOM,
    OUTPUT,
    SETTINGS,
)


def test_config_component_empty(mock_model: MagicMock):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Assert that the internal data is None
    assert component._data is None

    # When asking for data property, it should return a dict
    assert isinstance(component.data, Settings)
    assert isinstance(component._data, Settings)  # Same for internal
    assert component.data.hazard is None


def test_config_component_props(tmp_path: Path, mock_model: MagicMock):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Assert it's properties
    assert component.dir == tmp_path
    assert component.filename == f"{SETTINGS}.toml"
    # Set the filename
    component.filename = "foo.toml"
    assert component.filename == "foo.toml"
    # Set the output directory
    component.output_dir = "output/foo"
    assert component.output_dir == Path(tmp_path, "output", "foo")


def test_config_component_clear(
    mock_model: MagicMock,
    config_dummy: dict,
):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Set data like a dummy
    component.data.output.path = Path("foo")
    # Assert the current state
    assert component.data.output.path == Path("foo")

    # Call the clear method
    component.clear()
    # Assert the state after
    assert component.data.output.path == Path(OUTPUT)


def test_config_component_read(
    mock_model: MagicMock,
    model_data_clipped_path: Path,
):
    # Set it to read mode
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )

    # Setup the component
    component = ConfigComponent(mock_model)

    # Assert its data currently none
    assert component._data is None

    # Read the data
    component.read()

    # Assert the read data
    assert isinstance(component.data, Settings)
    assert component.data.model.type == GEOM
    assert component.data.exposure.geom


def test_config_component_read_none(
    mocker: MockerFixture,
    mock_model: MagicMock,
):
    # Set it to read mode
    mocker.patch.object(
        type(mock_model.root),
        "mode",
        new_callable=PropertyMock,
        return_value=ModelMode("r"),
    )

    # Setup the component
    component = ConfigComponent(mock_model)

    # Assert its data currently none
    assert component._data is None

    # Read the data
    component.read()

    # Assert the read data
    assert isinstance(component.data, Settings)
    assert component.data.hazard is None
    assert component.data.exposure.geom is None


def test_config_component_write(
    tmp_path: Path,
    mock_model: MagicMock,
    config_dummy: dict,
):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Set data like a dummy
    component._data = Settings.model_validate(config_dummy)

    # Write the data
    component.write()

    # That the file exists
    assert Path(tmp_path, component._filename).is_file()

    # Assert at least the path that was absolute in the config dict
    data = read_toml(Path(tmp_path, component._filename))
    assert data["hazard"]["file"] == "foo.nc"


def test_config_component_write_sig(
    tmp_path: Path,
    mock_model: MagicMock,
):
    # Setup the component
    component = ConfigComponent(mock_model)
    # Set data like a dummy
    component._data = Settings()

    # Write to an alternative path
    component.write(filename="settings/tmp.toml")

    # That the file exists
    assert Path(tmp_path, "settings").is_dir()
    assert Path(tmp_path, "settings/tmp.toml").is_file()


def test_config_component_write_warnings(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    mock_model: MagicMock,
):
    caplog.set_level(logging.WARNING)
    # Setup the component
    component = ConfigComponent(mock_model)

    # Write the data
    component.write()

    # Assert the logging message
    assert "No alterations were made to the default settings" in caplog.text
    # Assert file has still been written
    assert Path(tmp_path, component._filename).is_file()


def test_config_component_update(
    tmp_path: Path,
    mock_model: MagicMock,
    config_dummy: dict[str, Any],
):
    # Setup the component
    component = ConfigComponent(mock_model)
    # Assert current state
    assert component.data.model.threads == 1
    assert component.data.hazard is None

    # Call update method
    component.update(**config_dummy)
    # Assert the state after
    assert component.data.model.threads == 4
    assert component.data.hazard.file == Path(tmp_path, "foo.nc")
