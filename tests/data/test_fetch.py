import os
from pathlib import Path

import pytest

from hydromt_fiat.data import fetch_data


def test_fetch_data():
    # Call the function in it's default state
    path = fetch_data(data="fiat-model-c")

    # Get the cache dir location
    cache_dir = Path("~", ".cache", "hydromt_fiat").expanduser()
    data_dir = Path(cache_dir, "fiat-model-c")

    # Assert the output
    assert Path(cache_dir, "fiat-model-c.tar.gz").is_file()
    assert data_dir.is_dir()
    assert data_dir == path
    assert Path(data_dir, "exposure").is_dir()
    assert Path(data_dir, "settings.toml").is_file()


def test_fetch_data_directory(tmp_path: Path):
    # Call the function in it's default state
    path = fetch_data(data="fiat-model-c", output_dir=tmp_path)

    # Get the cache dir location
    cache_dir = Path("~", ".cache", "hydromt_fiat").expanduser()
    data_dir = Path(tmp_path, "fiat-model-c")

    # Assert the output
    assert Path(cache_dir, "fiat-model-c.tar.gz").is_file()
    assert data_dir.is_dir()
    assert data_dir == path
    assert Path(data_dir, "exposure").is_dir()
    assert Path(data_dir, "settings.toml").is_file()


def test_fetch_data_no_subdir(tmp_path: Path):
    # Call the function in it's default state
    path = fetch_data(data="fiat-model-c", output_dir=tmp_path, sub_dir=False)

    # Get the cache dir location
    cache_dir = Path("~", ".cache", "hydromt_fiat").expanduser()

    # Assert the output
    assert Path(cache_dir, "fiat-model-c.tar.gz").is_file()
    assert tmp_path == path
    assert Path(tmp_path, "exposure").is_dir()
    assert Path(tmp_path, "settings.toml").is_file()


def test_fetch_data_relative(tmp_path: Path):
    # Set the cwd
    cur_cwd = Path.cwd()
    os.chdir(tmp_path)

    # Call the function in it's default state
    path = fetch_data(data="fiat-model-c", output_dir="data", sub_dir=False)

    # Get the cache dir location
    cache_dir = Path("~", ".cache", "hydromt_fiat").expanduser()
    data_dir = Path(tmp_path, "data")

    # Assert the output
    assert Path(cache_dir, "fiat-model-c.tar.gz").is_file()
    assert data_dir == path
    assert Path(data_dir, "exposure").is_dir()
    assert Path(data_dir, "settings.toml").is_file()

    # Change the cwd back
    os.chdir(cur_cwd)


def test_fetch_data_errors():
    # Call the function while requesting something that isnt there
    with pytest.raises(
        ValueError,
        match="Choose one of the following: ",
    ):
        fetch_data(data="foobar")
