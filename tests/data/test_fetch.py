import os
from pathlib import Path

import pytest
from pooch.processors import ExtractorProcessor

from hydromt_fiat.data.fetch import _fetch_registry, _unpack_processor, fetch_data
from tests.conftest import check_connection


def test__fetch_registry_local():
    # Call the function
    db = _fetch_registry(local_registry=True)

    # Assert the output
    assert isinstance(db, dict)
    assert "data" in db


@check_connection
def test__fetch_registry_remote():
    # Call the function
    db = _fetch_registry(local_registry=False)

    # Assert the output
    assert isinstance(db, dict)
    assert "data" in db


def test__unpack_processor_known():
    # Call the function
    up = _unpack_processor(suffix="tar.gz")

    # Assert the output
    assert isinstance(up, ExtractorProcessor)


def test__unpack_processor_unknown():
    # Call the function
    up = _unpack_processor(suffix="foo")

    # Assert the output
    assert up is None

@check_connection
def test_fetch_data():
    # Call the function in it's default state
    path = fetch_data(data="fiat-model-c", retries=1)

    # Get the cache dir location
    cache_dir = Path("~", ".cache", "hydromt_fiat").expanduser()
    data_dir = Path(cache_dir, "fiat-model-c")

    # Assert the output
    assert Path(cache_dir, "fiat-model-c.tar.gz").is_file()
    assert data_dir.is_dir()
    assert data_dir == path
    assert Path(data_dir, "exposure").is_dir()
    assert Path(data_dir, "settings.toml").is_file()

@check_connection
def test_fetch_data_directory(tmp_path: Path):
    # Call the function in it's default state
    path = fetch_data(data="fiat-model-c", output_dir=tmp_path, retries=1)

    # Get the cache dir location
    cache_dir = Path("~", ".cache", "hydromt_fiat").expanduser()
    data_dir = Path(tmp_path, "fiat-model-c")

    # Assert the output
    assert Path(cache_dir, "fiat-model-c.tar.gz").is_file()
    assert data_dir.is_dir()
    assert data_dir == path
    assert Path(data_dir, "exposure").is_dir()
    assert Path(data_dir, "settings.toml").is_file()

@check_connection
def test_fetch_data_no_subdir(tmp_path: Path):
    # Call the function in it's default state
    path = fetch_data(data="fiat-model-c", output_dir=tmp_path, sub_dir=False, retries=1)

    # Get the cache dir location
    cache_dir = Path("~", ".cache", "hydromt_fiat").expanduser()

    # Assert the output
    assert Path(cache_dir, "fiat-model-c.tar.gz").is_file()
    assert tmp_path == path
    assert Path(tmp_path, "exposure").is_dir()
    assert Path(tmp_path, "settings.toml").is_file()

@check_connection
def test_fetch_data_relative(tmp_path: Path):
    # Set the cwd
    cur_cwd = Path.cwd()
    os.chdir(tmp_path)

    # Call the function in it's default state
    path = fetch_data(data="fiat-model-c", output_dir="data", sub_dir=False, retries=1)

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

@check_connection
def test_fetch_data_errors():
    # Call the function while requesting something that isnt there
    with pytest.raises(
        ValueError,
        match="Choose one of the following: ",
    ):
        fetch_data(data="foobar")
