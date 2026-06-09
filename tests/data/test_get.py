import os
from pathlib import Path

import pytest
import requests

from hydromt_fiat.data import fetch_data
from hydromt_fiat.data.get import (
    BUCKET,
    CLIENT,
    assert_remote_hash,
    check_local_hash,
    download,
    get_entry,
    get_registry,
)
from hydromt_fiat.utils import PATH, VERSION
from tests.conftest import CACHE_DIR, check_connection


def test_get_registry_local():
    # Call the function
    db = get_registry(local=True)

    # Assert the output
    assert isinstance(db, dict)
    assert "global-data.tar.gz" in db


@check_connection(error=False)
def test_get_registry_remote():
    # Call the function
    db = get_registry(local=False)

    # Assert the output
    assert isinstance(db, dict)
    assert "fiat-model.tar.gz" in db


def test_get_entry(
    registry: dict[str, dict[str, str]],
):
    # Call the function
    n, e = get_entry(name="global-data.tar.gz", registry=registry)
    # Assert the output
    assert n == "global-data.tar.gz"
    assert isinstance(e, dict)
    assert e["path"] == "global-data"


def test_get_entry_by_stem(
    registry: dict[str, dict[str, str]],
):
    # Call the function with the stem of the file
    n, e = get_entry(name="global-data", registry=registry)
    # Assert the same output
    assert n == "global-data.tar.gz"
    assert isinstance(e, dict)
    assert e["path"] == "global-data"


def test_get_entry_errors(
    registry: dict[str, dict[str, str]],
):
    # Call the function with the invalid input
    with pytest.raises(
        KeyError,
        match="'foo' is not found in the registry, directly or by stem",
    ):
        get_entry(name="foo", registry=registry)


@check_connection(error=False)
def test_assert_remote_hash(registry: dict[str, dict[str, str]]):
    file = "global-data.tar.gz"
    entry = registry[file]
    # Get the stats from the bucket
    stat = CLIENT.head_object(
        Bucket=BUCKET,
        Key=Path(entry[PATH], entry[VERSION], file).as_posix(),
    )
    # Call the function
    assert_remote_hash(stat=stat, known_hash=entry["hash"])
    # Should just pass


@check_connection(error=False)
def test_assert_remote_hash_errors(registry: dict[str, dict[str, str]]):
    file = "global-data.tar.gz"
    entry = registry[file]
    # Get the stats from the bucket
    stat = CLIENT.head_object(
        Bucket=BUCKET,
        Key=Path(entry[PATH], entry[VERSION], file).as_posix(),
    )
    # Call the function with a nonsense hash
    with pytest.raises(
        requests.RequestException,
        match="Requested file does not match the hash from the registry",
    ):
        assert_remote_hash(stat=stat, known_hash="foo")


def test_check_local_hash(registry: dict[str, dict[str, str]]):
    # Call the function with the file matching a hash
    f = check_local_hash(
        file=Path(CACHE_DIR, "global-data.tar.gz"),
        hash=registry["global-data.tar.gz"]["hash"],
    )
    # Assert that the flag is True
    assert f


def test_check_local_hash_unequal(
    tmp_tarfile: Path, registry: dict[str, dict[str, str]]
):
    assert tmp_tarfile.exists()
    # Call the function with the file matching a hash
    f = check_local_hash(
        file=tmp_tarfile,
        hash=registry["global-data.tar.gz"]["hash"],
    )
    # Assert that the flag is False and the file has been unlinked
    assert not f
    assert not tmp_tarfile.exists()


def test_check_local_hash_not_exist(tmp_path: Path):
    # Call the function on a file that doesnt exist
    f = check_local_hash(
        file=Path(tmp_path, "foo.json"),
        hash="bar",
    )
    # Assert the flag is False
    assert not f


@check_connection(error=False)
def test_download(
    tmp_path: Path,
    registry: dict[str, dict[str, str]],
):
    file = "global-data.tar.gz"
    p = Path(tmp_path, file)
    # Call the function
    download(
        file=file,
        entry=registry[file],
        write_path=p,
    )
    # Assert the output
    assert p.is_file()


@check_connection()
def test_fetch_data():
    # Call the function in it's default state
    path = fetch_data(name="fiat-model-c", cache_dir=CACHE_DIR)

    # Get the cache dir location
    data_dir = Path(CACHE_DIR, "fiat-model-c")

    # Assert the output
    assert Path(CACHE_DIR, "fiat-model-c.tar.gz").is_file()
    assert data_dir.is_dir()
    assert data_dir == path
    assert Path(data_dir, "exposure").is_dir()
    assert Path(data_dir, "settings.toml").is_file()


@check_connection(error=False)
def test_fetch_data_cache_dir(tmp_path: Path):
    # Call the function in it's default state
    path = fetch_data(name="fiat-model-c", cache_dir=tmp_path)

    # Get the cache dir location
    data_dir = Path(tmp_path, "fiat-model-c")

    # Assert the output
    assert Path(tmp_path, "fiat-model-c.tar.gz").is_file()
    assert data_dir.is_dir()
    assert data_dir == path
    assert Path(data_dir, "exposure").is_dir()
    assert Path(data_dir, "settings.toml").is_file()


def test_fetch_data_no_subdir(tmp_path: Path):
    # Call the function in it's default state
    path = fetch_data(
        name="fiat-model-c",
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
        name="fiat-model-c",
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
