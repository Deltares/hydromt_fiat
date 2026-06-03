import os
from pathlib import Path

import pytest

from hydromt_fiat.data import fetch_data
from hydromt_fiat.data.get import get_registry
from tests.conftest import CACHE_DIR, check_connection


def test_get_registry_local():
    # Call the function
    db = get_registry(local=True)

    # Assert the output
    assert isinstance(db, dict)
    assert "global-data.tar.gz" in db


@check_connection
def test_get_registry_remote():
    # Call the function
    db = get_registry(local=False)

    # Assert the output
    assert isinstance(db, dict)
    assert "data" in db


def test_fetch_data():
    # Call the function in it's default state
    path = check_connection(fetch_data)(data="fiat-model-c.tar.gz", cache_dir=CACHE_DIR)

    # Get the cache dir location
    data_dir = Path(CACHE_DIR, "fiat-model-c")

    # Assert the output
    assert Path(CACHE_DIR, "fiat-model-c.tar.gz").is_file()
    assert data_dir.is_dir()
    assert data_dir == path
    assert Path(data_dir, "exposure").is_dir()
    assert Path(data_dir, "settings.toml").is_file()


def test_fetch_data_no_subdir(tmp_path: Path):
    # Call the function in it's default state
    path = fetch_data(
        data="fiat-model-c.tar.gz",
        sub_dir=False,
        cache_dir=CACHE_DIR,
        output_dir=tmp_path,
    )

    # Assert the output
    assert Path(CACHE_DIR, "fiat-model-c.tar.gz").is_file()
    assert tmp_path == path
    assert Path(tmp_path, "exposure").is_dir()
    assert Path(tmp_path, "settings.toml").is_file()


def test_fetch_data_relative_output_dir(tmp_path: Path):
    # Set the cwd
    cur_cwd = Path.cwd()
    os.chdir(tmp_path)

    # Call the function in it's default state
    path = fetch_data(
        data="fiat-model-c.tar.gz",
        sub_dir=False,
        cache_dir=CACHE_DIR,
        output_dir="data",
    )

    # Get the cache dir location
    data_dir = Path(tmp_path, "data")

    # Assert the output
    assert Path(CACHE_DIR, "fiat-model-c.tar.gz").is_file()
    assert data_dir == path
    assert Path(data_dir, "exposure").is_dir()
    assert Path(data_dir, "settings.toml").is_file()

    # Change the cwd back
    os.chdir(cur_cwd)


def test_fetch_data_errors():
    # Call the function while requesting something that isnt there
    with pytest.raises(
        KeyError,
        match="",
    ):
        check_connection(fetch_data)(data="foobar")
