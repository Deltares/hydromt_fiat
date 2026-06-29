from pathlib import Path

from hydromt_fiat.components.utils import (
    _mount,
    _relpath,
    ensure_path_listing,
    make_config_paths_relative,
    pathing_config,
    pathing_expand,
)
from hydromt_fiat.settings import ExposureGeometry


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
    p = config_dummy["hazard"]["file"]
    assert Path(p).is_absolute()
    assert config_dummy["hazard"]["rp"] == [1, 2, 3]
    assert config_dummy["vulnerability"]["file"] == Path("foo.csv")

    # Call the function
    cfg = make_config_paths_relative(config_dummy, tmp_path)

    # Assert the outcome
    # Assert that a full path is present
    p = cfg["hazard"]["file"]
    assert not Path(p).is_absolute()  # Not anymore
    assert cfg["hazard"]["rp"] == [1, 2, 3]
    assert config_dummy["vulnerability"]["file"] == "foo.csv"


def test_ensure_path_listing():
    # Call the function
    p = ensure_path_listing("foo.txt")

    # Assert the output
    assert p == [Path("foo.txt")]


def test_ensure_path_listing_w_none():
    # Call the function
    p = ensure_path_listing(["foo.txt", None])

    # Assert the output
    assert p == [Path("foo.txt")]


def test_ensure_path_listing_none():
    # Call the function
    p = ensure_path_listing(None)

    # Assert the output
    assert p is None


def test_pathing_expand(
    model_data_clipped_path: Path,
):
    # Call the function
    paths, names = pathing_expand(
        root=model_data_clipped_path, filename="exposure/{name}.fgb"
    )
    # Assert the output
    assert len(paths) == 2
    assert len(names) == 2
    assert paths[0].suffix == ".fgb"

    # To a directory with no data
    # Call the function
    paths, names = pathing_expand(
        root=model_data_clipped_path, filename="foo/{name}.fgb"
    )
    # Assert the output
    assert len(paths) == 0
    assert len(names) == 0


def test_pathing_expand_none(
    model_data_clipped_path: Path,
):
    # Call the function
    out = pathing_expand(root=model_data_clipped_path, filename=None)
    # Assert the output
    assert out is None


def test_pathing_config():
    # Call the function
    paths, names = pathing_config(
        [ExposureGeometry(file="tmp.txt"), ExposureGeometry(file="foo.txt")]
    )
    # Assert the output
    assert all([isinstance(item, Path) for item in paths])
    assert names == ["tmp", "foo"]


def test_pathing_config_none():
    # Call the function
    out = pathing_config(None)
    # Assert the output
    assert out is None
