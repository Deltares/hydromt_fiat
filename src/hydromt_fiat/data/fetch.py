"""Data for examples and testing of HydroMT-FIAT."""

import json
import logging
from pathlib import Path
from typing import Any

import pooch
import requests
from pooch.processors import ExtractorProcessor

__all__ = ["fetch_data"]

logger = logging.getLogger(__name__)

PROCESSORS = {
    "tar.gz": pooch.Untar,
    "zip": pooch.Unzip,
}
REMOTE_REGISTRY = "https://raw.githubusercontent.com/Deltares/hydromt_fiat/refs/heads/main/src/hydromt_fiat/data/registry.json"


def _fetch_registry(
    local_registry: bool = True,
) -> dict[str, Any]:
    """Fetch the registry."""
    # Get the data either from the local repo or remote repo
    if local_registry:
        with open(Path(__file__).parent / "registry.json", "r") as f:
            data = f.read()
    else:
        r = requests.get(REMOTE_REGISTRY, timeout=5)
        data = r.text

    # Load the json data
    database = json.loads(data)
    return database


def _unpack_processor(
    suffix: str,
    extract_dir: Path | str = "./",
) -> ExtractorProcessor:
    """Select the right processor for unpacking."""
    if suffix not in PROCESSORS:
        return None
    processor = PROCESSORS[suffix](members=None, extract_dir=extract_dir)
    return processor


def fetch_data(
    data: str,
    local_registry: bool = True,
    sub_dir: bool = True,
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
    sub_dir : bool
        Whether to place the fetched data in a sub directory of the same name.
        I.e. if  the (tarred) dataset is named 'custom-data' a directory named
        'custom-data' is created in which the data are placed. By default True.
    output_dir : Path | str | None
        The output directory to store the data.
        If None, the data will be stored in ~/.cache/hydromt_fiat/<data>.

    Returns
    -------
    Path
        The output directory where the data is stored.
    """
    # Open the registry
    # update the base URL and registry with new versions of the data
    # use create_artifact.py script to create the build-data/ test-data archives
    database = _fetch_registry(local_registry=local_registry)
    base_url: str = database["url"]
    registry: dict[str, str] = database["data"]
    # Set the cache directory, for at the very least the tarball
    cache_dir = Path("~", ".cache", "hydromt_fiat").expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)

    if output_dir is None:
        output_dir = cache_dir
    output_dir = Path(output_dir)
    if not output_dir.is_absolute():
        output_dir = Path(Path.cwd(), output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Quick check whether the data can be found
    choices_raw = list(registry.keys())
    choices = [item.split(".", 1)[0] for item in choices_raw]
    if data not in choices:
        raise ValueError(f"Choose one of the following: {choices}")
    idx = choices.index(data)

    # Setup Pooch
    retriever = pooch.create(
        path=cache_dir,  # store archive to cache
        base_url=base_url,
        registry=registry,
    )

    # Set the way of unpacking it
    suffix = choices_raw[idx].split(".", 1)[1]
    extract_dir = output_dir
    if sub_dir:
        extract_dir = Path(extract_dir, data)
    processor = _unpack_processor(suffix, extract_dir=extract_dir)
    # Retrieve the data
    retriever.fetch(choices_raw[idx], processor=processor)

    return extract_dir
