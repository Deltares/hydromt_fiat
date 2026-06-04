"""Some data utility."""

import hashlib
from _hashlib import HASH
from pathlib import Path

__all__ = ["file_hash"]


def file_hash(
    path: Path,
    chunk_size: int = 50,
    hash_alg: str = "sha256",
) -> str:
    """Generate a hash from a local file.

    Parameters
    ----------
    path : Path
        The path to the file.
    chunk_size : int, optional
        The size of the chunks when reading the file. This number is in MegaBytes.
        By default 50.
    hash_alg : str, optional
        The hash algoritm to use, by default "sha256".

    Returns
    -------
    str
        The hash representing the file.
    """
    obj: HASH = getattr(hashlib, hash_alg)()
    # Convert to bytes
    bytes_size = chunk_size * (1024**2)
    # Read the file chunks and add it to md5 object
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(bytes_size), b""):
            obj.update(chunk)
    # Return the hash over the whole
    return obj.hexdigest()
