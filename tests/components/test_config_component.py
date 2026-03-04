import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
from hydromt.model import ModelRoot
from hydromt.readers import read_toml

from hydromt_fiat.components import ConfigComponent
from hydromt_fiat.utils import (
    EXPOSURE,
    GEOM,
    MODEL,
    SETTINGS,
    TYPE,
)


def test_config_component_empty(mock_model: MagicMock):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Assert that the internal data is None
    assert component._data is None

    # When asking for data property, it should return a dict
    assert isinstance(component.data, dict)
    assert isinstance(component._data, dict)  # Same for internal
    assert len(component.data) == 0


def test_config_component_props(tmp_path: Path, mock_model: MagicMock):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Assert it's properties
    assert component.dir == tmp_path
    assert component.filename == f"{SETTINGS}.toml"
    # Set the filename
    component.filename = "foo.toml"
    assert component.filename == "foo.toml"


def test_config_component_clear(
    mock_model: MagicMock,
    config_dummy: dict,
):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Set data like a dummy
    component._data = config_dummy
    # Assert the current state
    assert len(component.data) == 4

    # Call the clear method
    component.clear()
    # Assert the state after
    assert len(component.data) == 0


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


def test_config_component_set_dict(
    mock_model: MagicMock,
):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Set data
    component.set("foo.bar", value="baz")
    # Assert state
    assert component.data["foo"]["bar"] == "baz"

    # Set data via a dictionary
    component.set("foo", value={"boo": 2})
    # Assert state
    assert component.data["foo"]["boo"] == 2
    assert len(component.data["foo"]) == 2


def test_config_component_set_none(
    mock_model: MagicMock,
):
    # Setup the component
    component = ConfigComponent(mock_model)

    # Set data
    component.set("foo", value=None)
    # Assert state
    assert "foo" not in component.data

    # Set data via a dictionary
    component.set("foo", value={"bar": 2, "boo": None})
    # Assert state
    assert "bar" in component.data["foo"]
    assert "boo" not in component.data["foo"]
    assert len(component.data["foo"]) == 1


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
    assert isinstance(component.data, dict)
    assert len(component.data) == 4
    assert component.data[MODEL][TYPE] == GEOM
    assert component.data[EXPOSURE]


def test_config_component_read_none(
    tmp_path: Path,
    mock_model: MagicMock,
):
    # Set it to read mode
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(tmp_path, mode="r"),
    )

    # Setup the component
    component = ConfigComponent(mock_model)

    # Assert its data currently none
    assert component._data is None

    # Read the data
    component.read()

    # Assert the read data
    assert isinstance(component.data, dict)
    assert len(component.data) == 0


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
    data = read_toml(Path(tmp_path, component._filename))
    assert data["baz"]["file1"] == "tmp.txt"


def test_config_component_write_sig(
    tmp_path: Path,
    mock_model: MagicMock,
):
    # Setup the component
    component = ConfigComponent(mock_model)
    # Set data like a dummy
    component._data = {"foo": "bar"}

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
    assert "No data in config component, writing empty file.." in caplog.text
    # Assert file has still been written
    assert Path(tmp_path, component._filename).is_file()
