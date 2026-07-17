from pathlib import Path

from hydromt_fiat.settings.exposure import ExposureGeometry
from hydromt_fiat.settings.utils import _mount, _relpath, get_config_list_files


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
    in_p = Path(tmp_path.parent, "tmp.txt")
    p = _relpath(in_p, tmp_path)

    # Assert the output
    assert p == "../tmp.txt"


def test__relpath_abs_5(tmp_path: Path):
    porig = Path(tmp_path, "tmp/tmp/tmp/tmp/tmp/tmp/tmp/tmp.txt")
    # Call the function, while far away from the our path
    p = _relpath(porig, tmp_path)

    # Assert the output
    assert isinstance(p, str)
    assert p == porig.as_posix()


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


def test_get_config_list_files():
    # Call the function
    paths = get_config_list_files(
        [ExposureGeometry(file="tmp.txt"), ExposureGeometry(file="foo.txt")]
    )
    # Assert the output
    assert len(paths) == 2
    assert all([isinstance(item, Path) for item in paths])


def test_get_config_list_files_none():
    # Call the function
    out = get_config_list_files(None)
    # Assert the output
    assert out is None
