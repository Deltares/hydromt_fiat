"""Component utilities."""

import os
import re
from os.path import relpath
from pathlib import Path
from typing import Any

from hydromt._utils.naming_convention import _expand_uri_placeholders
from hydromt.model.components import ConfigComponent

MOUNT_PATTERN = re.compile(r"(^\/(\w+)\/|^(\w+):\/).*$")


## Config/ pathing related
def _mount(
    value: str,
) -> str | None:
    """Get the mount of a path."""
    m = MOUNT_PATTERN.match(value)
    if m is None:
        return None
    return m.group(1)


def _relpath(
    value: Any,
    root: Path,
) -> str | Any:
    """Generate a relative path."""
    if not isinstance(value, (Path, str)) or not Path(value).is_absolute():
        return value
    value = Path(value)
    try:
        if _mount(value.as_posix()) == _mount(root.as_posix()):
            value = Path(relpath(value, root))
    except ValueError:
        pass  # `value` path is not relative to root
    return value.as_posix()


def make_config_paths_relative(
    data: dict,
    root: Path,
) -> dict:
    """Make the configurations path relative to the root.

    This only concerns itself with paths that are absolute and on
    the same mount.

    Parameters
    ----------
    data : dict
        The configurations in a dictionary format.
    root : Path
        The root to which the paths are made relative.
        Most of the time, this will be the parent directory of the
        configurations file.
    """
    for key, val in data.items():
        if isinstance(val, list) and all([isinstance(item, dict) for item in val]):
            for item in val:
                make_config_paths_relative(item, root)
        if isinstance(val, dict):
            data.update({key: make_config_paths_relative(val, root)})
        else:
            data.update({key: _relpath(val, root)})
    return data


def config_file_entry(
    cfg: ConfigComponent,
    entry: str,
) -> Path | None:
    """Get file entry from config.

    Parameters
    ----------
    cfg : ConfigComponent
        The config component of the model.
    entry : str
        Requested value paired with this entry.
    """
    # Return None if None
    if cfg is None:
        return
    value = cfg.get_value(entry)
    # Return None if None
    if value is None:
        return
    # File check
    value = Path(value)
    root = Path(cfg.model.root.path, cfg._filename).parent
    if not value.is_absolute():
        value = Path(root, value)
    if value.is_file():
        return value
    return


def get_item(
    parts: list,
    current: dict,
    root: Path | str,
    fallback: Any | None = None,
    abs_path: bool = False,
) -> Any | None:
    """Get item from a dictionary."""
    num_parts = len(parts)
    for i, part in enumerate(parts):
        if isinstance(current, list):
            return [
                get_item(parts[i:], item, root, fallback, abs_path) for item in current
            ]
        if i < num_parts - 1:
            current = current.get(part, {})
        else:
            value = current.get(part, fallback)
            if abs_path and isinstance(value, (Path, str)):
                value = Path(root, value)
            return value


def pathing_expand(root: Path, filename: str | None = None) -> tuple[list]:
    """Sort the pathing on reading based on a wildcard."""
    # If the filename is None, do nothing
    if filename is None:
        return
    # Expand
    path_glob, _, regex = _expand_uri_placeholders(filename)
    p = list(Path(root).glob(path_glob))
    n = []
    # Get the unique names
    for item in p:
        rel = Path(os.path.relpath(item, root))
        name = ".".join(regex.match(rel.as_posix()).groups())
        n.append(name)
    return p, n


def pathing_config(p: list | str | None):
    """Sort pathing based on config entries (i.e. a list)."""
    # Handling legacy configs
    if not isinstance(p, list):
        p = list(p)
    # If no files return None
    if all([item is None for item in p]):
        return
    # Remove entries with no files and get the names of the remaining ones
    p = [item for item in p if item is not None]
    n = [item.stem for item in p]
    return p, n
