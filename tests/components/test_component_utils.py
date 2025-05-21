from pathlib import Path

from hydromt_fiat import FIATModel
from hydromt_fiat.components.utils import config_file_entry


def test_config_file_entry_no_config():
    # Call the function
    res = config_file_entry(None, "entry")

    # Assert its None
    assert res is None


def test_config_file_entry_no_value(
    model: FIATModel,
):
    # Call the function
    res = config_file_entry(model.config, "entry")

    # Assert its None
    assert res is None


def test_config_file_entry_no_file_return(
    tmp_path: Path,
    model: FIATModel,
):
    # Set and entry to return
    model.config.set("path_to_file", Path(tmp_path, "tmp.unknown"))
    # Call the function
    res = config_file_entry(model.config, "path_to_file")

    # Assert its None
    assert res is None


def test_config_file_entry_return(
    model: FIATModel,
    model_cached: Path,
):
    # Set and entry to return
    model.config.set("path_to_file", Path(model_cached, "region.geojson"))
    # Call the function
    res = config_file_entry(model.config, "path_to_file")

    # Assert its None
    assert res is not None
    assert isinstance(res, Path)


def test_config_file_entry_rel_return(
    model: FIATModel,
    model_cached: Path,
):
    # Set and entry to return
    model.root.set(model_cached, mode="r")
    # Call the function
    res = config_file_entry(model.config, "exposure.geom.file1")

    # Assert its None
    assert res is not None
    assert isinstance(res, Path)
