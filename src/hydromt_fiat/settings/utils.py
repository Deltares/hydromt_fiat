"""Some utility for the settings."""

import re
from pathlib import Path
from typing import Any, Protocol

MOUNT_PATTERN = re.compile(r"(^\/(\w+)\/|^(\w+):\/).*$")


class FileModel(Protocol):
    """Simple type hinting helper."""

    file: Path


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
    if not isinstance(value, Path):
        return value
    value = Path(value)
    if _mount(value.as_posix()) == _mount(root.as_posix()):
        value_rel = value.relative_to(root, walk_up=True)
        if len(value_rel.parts) < 5:
            return value_rel.as_posix()
    return value.as_posix()


def get_config_list_files(
    config_files: list[FileModel] | None,
) -> list[Path] | None:
    """Sort pathing based on config entries (i.e. a list)."""
    if config_files is None:
        return None
    # Remove entries with no files and get the names of the remaining ones
    p = [item.file for item in config_files]
    return p
