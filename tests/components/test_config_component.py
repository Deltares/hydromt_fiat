import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
from hydromt._io import _read_toml
from hydromt.model import ModelRoot

from hydromt_fiat.components import ConfigComponent


def test_config_component_init(mock_model: MagicMock):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Assert that the internal data is None
    assert component._data is None

    # When asking for data property, it should return a tomlkit document
    assert isinstance(component.data, dict)
    assert isinstance(component._data, dict)  # Same for internal
    assert len(component.data) == 0


def test_config_component_props(tmp_path: Path, mock_model: MagicMock):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Assert it's properties
    assert component.dir == tmp_path
    assert component.filename == "settings.toml"
    # Set the filename
    component.filename = "foo.toml"
    assert component.filename == "foo.toml"


def test_config_component_get(
    mock_model: MagicMock,
    config_dummy: dict,
):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Set data like a dummy
    component._data = config_dummy

    # Get an entry
    res = component.get("foo")
    # Assert the entry
    assert res == "bar"

    # Get an entry deeper
    res = component.get("spooky.ghost")
    # Assert the entry
    assert res == [1, 2, 3]

    # Get an entry that doesnt exists, return fallback
    res = component.get("No", fallback=2)
    # Assert the entry
    assert res == 2


def test_config_component_get_path(
    tmp_path: Path,
    mock_model: MagicMock,
    config_dummy: dict,
):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Set data like a dummy
    component._data = config_dummy

    # Get and entry as an absolute path
    res = component.get("baz.file2", abs_path=True)
    # Assert the output
    assert res == Path(tmp_path, "tmp/tmp.txt")


def test_config_component_set(
    mock_model: MagicMock,
):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Set data
    component.set("foo", value="bar")
    # Assert state
    assert component.data["foo"] == "bar"

    # Set data with an extra level (part)
    component.set("baz.boo", value=2)
    # Assert state
    assert component.data["baz"]["boo"] == 2


def test_config_component_read(
    mock_model: MagicMock,
    model_cached: Path,
):
    # Set it to read mode
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_cached, mode="r"),
    )

    # Setup the component
    component = ConfigComponent(mock_model)

    # Assert its data currently none
    assert component._data is None

    # Read the data
    component.read()

    # Assert the read data
    assert isinstance(component.data, dict)
    assert len(component.data) == 4
    assert component.data["model"]["model_type"] == "geom"
    assert component.data["exposure"]


def test_config_component_write(
    tmp_path: Path,
    mock_model: MagicMock,
    config_dummy: dict,
):
    # Setup the component
    component = ConfigComponent(mock_model)

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
    assert "No data in config component, skip writing" in caplog.text
    # Assert no file has been written
    assert not Path(tmp_path, component._filename).is_file()
