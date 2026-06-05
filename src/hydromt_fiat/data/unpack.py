"""Small module for unpacking archives."""

import tarfile
import zipfile
from pathlib import Path
from tarfile import TarInfo
from typing import Callable

__all__ = ["untar", "unzip"]


def _is_archive(
    file: Path,
) -> tuple[bool, bool]:
    """Check whether it's an archive."""
    return (tarfile.is_tarfile(file), zipfile.is_zipfile(file))


def _dummy_filter(tarinfo, path=None):
    """Do nothing."""
    return tarinfo


def untar(
    file: Path,
    filter: Callable[[TarInfo, str], TarInfo | None] | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Unpack a tar archive.

    Parameters
    ----------
    file : Path
        The path of the tar archive.
    filter : Callable, optional
        A custom filter to filter the data to unpack. If no filter is provided
        all data are unpacked. By default None.
    output_dir : Path | None, optional
        The output directory in which to extract the contents. If not provided,
        the contents are extracted in the same directory as the archive.
        By default None.

    Returns
    -------
    Path
        The path of the extracted contents.
    """
    # Check the validity of the file
    if not tarfile.is_tarfile(file):
        raise tarfile.TarError(f"'{file.as_posix()}' is not a tar file.")
    # Ensure the output directory
    output_dir = output_dir or file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    # Untar it
    with tarfile.open(file) as archive:
        archive.extractall(path=output_dir, filter=(filter or _dummy_filter))
    return output_dir


def unzip(
    file: Path,
    output_dir: Path | None = None,
) -> Path:
    """Unpack a zip archive.

    Parameters
    ----------
    file : Path
        The path of the zip archive.
    output_dir : Path | None, optional
        The output directory in which to extract the contents. If not provided,
        the contents are extracted in the same directory as the archive.
        By default None.

    Returns
    -------
    Path
        The path of the extracted contents.
    """
    # Check the validity of the file
    if not zipfile.is_zipfile(file):
        raise zipfile.error(f"'{file.as_posix()}' is not a zip file.")
    # Ensure the output directory
    output_dir = output_dir or file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    # Untar it
    with zipfile.ZipFile(file, mode="r") as archive:
        archive.extractall(path=output_dir)
    return output_dir
