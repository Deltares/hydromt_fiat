"""Download data from minio s3 bucket."""

import json
import logging
import os
from pathlib import Path
from typing import Any

import requests
from minio import Minio, datatypes

from hydromt_fiat.data.unpack import is_archive, untar, unzip
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
HERE = Path(__file__).parent
REMOTE_REGISTRY = "https://raw.githubusercontent.com/Deltares/hydromt_fiat/refs/heads/main/src/hydromt_fiat/data/registry.json"

# Keys
with open(Path(HERE, "access.key"), "r") as reader:
    ACCESS_KEY = reader.read()
with open(Path(HERE, "secret.key"), "r") as reader:
    SECRET_KEY = reader.read()

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
        with open(Path(__file__).parent / f"{REGISTRY}.json", "r") as f:
            data = f.read()
    else:
        r = requests.get(REMOTE_REGISTRY, timeout=5)
        data = r.text

    # Load the json data
    database = json.loads(data)
    return database


def check_remote_hash(
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
        f"Checking whether {file.as_posix()} is already locally cached \
with correct hash"
    )
    if not file.exists():
        return False
    flag = file_hash(file, hash_alg=HASH_ALGORITM) == hash
    if not flag:
        os.unlink(file)
        return flag
    logger.info(f"Existing file: '{file.as_posix()}' matches the hash {hash}")
    return flag


def download(
    data: str,
    entry: dict[str, str],
    write_path: Path,
):
    # Checking for the remote hash match
    check_remote_hash(
        CLIENT.stat_object(
            BUCKET,
            Path(entry[PATH], entry[VERSION], data).as_posix(),
        ),
        known_hash=entry[HASHKEY],
    )

    logger.info(f"Downloading {data}..")
    # Get and write the as a stream from the bucket
    respone = CLIENT.get_object(
        BUCKET,
        Path(entry[PATH], entry[VERSION], data).as_posix(),
        data,
    )
    # Read chunks of the data and write those chunks
    with open(write_path, "wb") as writer:
        for chunk in respone.stream(50 * 1024**2):
            writer.write(chunk)

    # Close off
    respone.close()
    respone.release_conn()


def fetch_data(
    data: str,
    local_registry: bool = True,
    sub_dir: bool = True,
    cache_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> Path:
    """Fetch data by simply calling the function.

    Parameters
    ----------
    data : str
        The data to fetch.
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
    logger.info(f"Requesting the {data} file from the {BUCKET} s3 bucket")
    # Get the registy
    registry = get_registry(local=local_registry)
    # Get the data entry from the registry
    entry = registry[data]
    # Use common cache directory or a user provided one
    cache_dir = cache_dir or CACHE_DIR
    # Set the output_dir
    output_dir = Path(Path.cwd(), output_dir) or cache_dir
    if sub_dir:
        output_dir = Path(output_dir, data.split(".", 1)[0])

    # Set the archive write path
    write_path = Path(cache_dir, data)
    # Check for the existence of the file
    if not check_local_hash(
        Path(cache_dir, data),
        hash=entry[HASHKEY],
    ):
        logger.info("File not locally cached, trying to download")
        # If not, download
        download(
            data=data,
            entry=entry,
            write_path=write_path,
        )

    # Unpack the data
    logger.info(f"Unpacking the archive to {output_dir.as_posix()}")
    archive_flag = is_archive(write_path)
    if any(archive_flag):
        UNPACK[archive_flag.index(True)](
            file=write_path,
            output_dir=output_dir,
        )
    # Return the output directory
    return output_dir


if __name__ == "__main__":
    from hydromt import log

    log.initialize_logging()
    x = file_hash(
        "c:/dev/data/hydromt_fiat/tarballs/global-data.tar.gz",
    )
    fetch_data("osmnx.tar.gz")
    pass
