"""Download data from minio s3 bucket."""

import json
import logging
import os
from pathlib import Path
from typing import Any

import requests
from minio import Minio, datatypes

from hydromt_fiat.data.unpack import _is_archive, untar, unzip
from hydromt_fiat.data.utils import file_hash
from hydromt_fiat.utils import PATH, REGISTRY, VERSION

__all__ = ["fetch_data"]

logger = logging.getLogger(f"hydromt.{__name__}")

# Settings
BUCKET = "hydromt-fiat"
CACHE_DIR = Path("~", ".cache", "hydromt_fiat").expanduser()
ENDPOINT = "s3.deltares.nl"
HASH_ALGORITM = "md5"
HASHKEY = "hash"
LIB_DATA_DIR = Path(__file__).parent
REMOTE_REGISTRY = "https://raw.githubusercontent.com/Deltares/hydromt_fiat/refs/heads/main/src/hydromt_fiat/data/registry.json"

# Keys
with open(Path(LIB_DATA_DIR, "access.key"), "r") as reader:
    ACCESS_KEY = reader.read().strip()
with open(Path(LIB_DATA_DIR, "secret.key"), "r") as reader:
    SECRET_KEY = reader.read().strip()

# Client
CLIENT = Minio(
    endpoint=ENDPOINT,
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    secure=True,  # Right? :p
)
# Unpack dictionary
UNPACK = {
    0: untar,
    1: unzip,
}


def get_registry(
    local: bool = True,
) -> dict[str, dict[str, Any]]:
    """Get the registry."""
    # Get the data either from the local repo or remote repo
    if local:
        with open(LIB_DATA_DIR / f"{REGISTRY}.json", "r") as f:
            data = f.read()
    else:
        r = requests.get(REMOTE_REGISTRY, timeout=5)
        data = r.text

    # Load the json data
    database = json.loads(data)
    return database


def get_entry(
    name: str, registry: dict[str, dict[str, str]]
) -> tuple[str, dict[str, str]]:
    """Get the entry from the registry."""
    if name in registry:
        return name, registry[name]
    name_map = {item.split(".", 1)[0]: item for item in registry.keys()}
    if name in name_map:
        file = name_map[name]
        return file, registry[file]
    raise KeyError(f"'{name}' is not found in the registry, directly or by stem")


def assert_remote_hash(
    stat: datatypes.Object,
    known_hash: str,
) -> None:
    """Check remote hash match.

    Done between the file in the bucket in the known hash from the registry.
    """
    if stat.etag != known_hash:
        raise requests.RequestException(
            "Requested file does not match the hash from the registry",
        )


def check_local_hash(
    file: Path,
    hash: str,
) -> bool:
    """Check local hash match.

    Done between a local file and the known hash from the registry.
    """
    logger.info(
        f"Checking whether '{file.name}' is already locally cached \
with correct hash"
    )
    if not file.exists():
        return False
    flag = file_hash(file, hash_alg=HASH_ALGORITM) == hash
    if not flag:
        os.unlink(file)
        return flag
    logger.info(f"Existing file: '{file.name}' matches the hash {hash}")
    return flag


def download(
    file: str,
    entry: dict[str, str],
    write_path: Path,
):
    """Download data from the minio bucket.

    Parameters
    ----------
    file : str
        The file to download.
    entry : dict[str, str]
        The entry from the registry corresponding to the file.
    write_path : Path
        The path to which to write the file.
    """
    # Checking for the remote hash match
    assert_remote_hash(
        CLIENT.stat_object(
            BUCKET,
            Path(entry[PATH], entry[VERSION], file).as_posix(),
        ),
        known_hash=entry[HASHKEY],
    )

    logger.info(f"Downloading {file}..")
    # Get and write the as a stream from the bucket
    respone = CLIENT.get_object(
        BUCKET,
        Path(entry[PATH], entry[VERSION], file).as_posix(),
    )
    logger.info(f"Writing file to '{write_path.as_posix()}'")
    # Read chunks of the data and write those chunks
    with open(write_path, "wb") as writer:
        for chunk in respone.stream(50 * 1024**2):
            writer.write(chunk)

    # Close off
    respone.close()
    respone.release_conn()


def fetch_data(
    name: str,
    local_registry: bool = True,
    sub_dir: bool = True,
    cache_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> Path:
    """Fetch data by simply calling this function.

    Parameters
    ----------
    name : str
        The name of the data to fetch, this can either be the file as defined in
        the registry file (e.g. 'global-data.tar.gz') or the stem of that file
        ('global-data').
    local_registry : bool, optional
        If True, the registry is taken from the current library location.
        Otherwise, it is taken from the remote 'main' branch on github, by default True.
    sub_dir : bool, optional
        Whether to place the fetched data in a sub directory of the same name.
        I.e. if  the (tarred) dataset is named 'custom-data' a directory named
        'custom-data' is created in which the data are placed. By default True.
    cache_dir : Path | str, optional
        The directory in which the tarball is stored.
        If None, the tarball is stored in ~/.cache/hydromt_fiat. By default None.
    output_dir : Path | str, optional
        The output directory to store the unpacked data.
        If None, the data will be stored in ~/.cache/hydromt_fiat/<data>.
        By default None.

    Returns
    -------
    Path
        The output directory where the data is stored.
    """
    logger.info(f"Requesting the '{name}' file from the {BUCKET} s3 bucket")
    # Get the registy
    registry = get_registry(local=local_registry)
    # Get the data entry from the registry
    file, entry = get_entry(name=name, registry=registry)
    # Use common cache directory or a user provided one
    cache_dir = cache_dir or CACHE_DIR
    # Set the output_dir
    output_dir = Path(Path.cwd(), output_dir or cache_dir)
    if sub_dir:
        output_dir = Path(output_dir, file.split(".", 1)[0])

    # Set the archive write path
    write_path = Path(cache_dir, file)
    # Check for the existence of the file
    if not check_local_hash(
        Path(cache_dir, file),
        hash=entry[HASHKEY],
    ):
        logger.info("File not locally cached, trying to download")
        # If not, download
        download(
            file=file,
            entry=entry,
            write_path=write_path,
        )

    # Unpack the data
    archive_flag = _is_archive(write_path)
    if any(archive_flag):
        logger.info(f"Unpacking the archive to {output_dir.as_posix()}")
        UNPACK[archive_flag.index(True)](
            file=write_path,
            output_dir=output_dir,
        )
    # Return the output directory
    return output_dir
