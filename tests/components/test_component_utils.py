from pathlib import Path

from hydromt_fiat import FIATModel
from hydromt_fiat.components.utils import (
    _mount,
    _relpath,
    config_file_entry,
    make_config_paths_relative,
)


def test__mount():
    # Call the function on unix path
    m = _mount("/d/tmp/foo")
    # Assert the mount
    assert m == "/d/"

    # Call the function on windows path
    m = _mount("d:/tmp/foo")
    # Assert the mount
    assert m == "d:/"

    # Call the function on a relative path
    m = _mount("tmp/foo")
    # Assert that it's None
    assert m is None


def test__relpath_abs(tmp_path: Path):
    # Call the function
    p = _relpath(Path(tmp_path, "tmp/tmp.txt"), tmp_path)

    # Assert the output
    assert isinstance(p, str)
    assert p == "tmp/tmp.txt"

    # Path one above the current, also pass as a string
    in_p = Path(tmp_path.parent, "tmp.txt").as_posix()
    p = _relpath(in_p, tmp_path)

    # Assert the output
    assert p == "../tmp.txt"


def test__relpath_rel(tmp_path: Path):
    # Call the function on a path that is already relative
    p = _relpath("tmp/tmp.txt", tmp_path)

    # Assert the output is just the same
    assert p == "tmp/tmp.txt"


def test__relpath_mount(tmp_path: Path, mount_string: str):
    # Call the function on a path that is located on another mount
    p = _relpath(Path(mount_string, "tmp", "tmp.txt"), tmp_path)

    # Assert the output is just the same
    assert p == f"{mount_string}tmp/tmp.txt"


def test__relpath_other(tmp_path: Path):
    # Call the function on value that could not be paths
    p = _relpath([2, 2], tmp_path)  # E.g. a list

    # Assert that the list is returned
    assert p == [2, 2]


def test_make_config_paths_relative(
    tmp_path: Path,
    config_dummy: dict,
):
    # Assert that a full path is present
    p = config_dummy["baz"]["file1"]
    assert Path(p).is_absolute()
    assert config_dummy["spooky"]["ghost"] == [1, 2, 3]
    assert config_dummy["baz"]["file2"] == "tmp/tmp.txt"

    # Call the function
    cfg = make_config_paths_relative(config_dummy, tmp_path)

    # Assert the outcome
    # Assert that a full path is present
    p = cfg["baz"]["file1"]
    assert not Path(p).is_absolute()  # Not anymore
    assert cfg["spooky"]["ghost"] == [1, 2, 3]
    assert cfg["baz"]["file2"] == "tmp/tmp.txt"


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
