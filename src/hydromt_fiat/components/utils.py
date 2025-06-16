"""Component utilities."""

import re
from os.path import relpath
from pathlib import Path
from typing import Any

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
):
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
        if isinstance(val, dict):
            data.update({key: make_config_paths_relative(val, root)})
        else:
            data.update({key: _relpath(val, root)})
    return data


def config_file_entry(
    cfg: ConfigComponent,
    entry: str,
):
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
