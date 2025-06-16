import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
from hydromt._io import _read_toml
from hydromt.model import ModelRoot

from hydromt_fiat.components import FIATConfigComponent


def test_fiat_config_component_init(mock_model: MagicMock):
    # Setup the component
    component = FIATConfigComponent(mock_model)

    # Assert that the internal data is None
    assert component._data is None

    # When asking for data property, it should return a tomlkit document
    assert isinstance(component.data, dict)
    assert isinstance(component._data, dict)  # Same for internal
    assert len(component.data) == 0


def test_fiat_config_component_read(
    mock_model: MagicMock,
    model_cached: Path,
):
    # Set it to read mode
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_cached, mode="r"),
    )

    # Setup the component
    component = FIATConfigComponent(mock_model)

    # Assert its data currently none
    assert component._data is None

    # Read the data
    component.read()

    # Assert the read data
    assert isinstance(component.data, dict)
    assert len(component.data) == 4
    assert component.data["model"]["model_type"] == "geom"
    assert component.data["exposure"]


def test_fiat_config_component_write(
    tmp_path: Path,
    mock_model: MagicMock,
    config_dummy: dict,
):
    # Setup the component
    component = FIATConfigComponent(mock_model)

    # Set data like a dummy
    component._data = config_dummy

    # Write the data
    component.write()

    # That the file exists
    assert Path(tmp_path, component._filename).is_file()

    # Assert at least the path that was absolute in the config dict
    data = _read_toml(Path(tmp_path, component._filename))
    assert data["baz"]["file1"] == "tmp.txt"

    # Write to an alternative path
    component.write(filename="settings/tmp.toml")

    # That the file exists
    assert Path(tmp_path, "settings").is_dir()
    assert Path(tmp_path, "settings/tmp.toml").is_file()


def test_fiat_config_component_write_warnings(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    mock_model: MagicMock,
):
    caplog.set_level(logging.WARNING)
    # Setup the component
    component = FIATConfigComponent(mock_model)

    # Write the data
    component.write()

    # Assert the logging message
    assert "No data in config component, skip writing" in caplog.text
    # Assert no file has been written
    assert not Path(tmp_path, component._filename).is_file()
