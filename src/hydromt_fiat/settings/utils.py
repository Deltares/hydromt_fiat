"""Some utility for the settings."""

import re
from os.path import relpath
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hydromt_fiat.settings.file import InputFileModel

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
    if not isinstance(value, Path):
        return value
    value = Path(value)
    if _mount(value.as_posix()) == _mount(root.as_posix()):
        value = Path(relpath(value, root))
        if len(value.parts) < 5:
            return value.as_posix()
    return value.as_posix()


def get_config_list_files(
    config_files: list["InputFileModel"] | None,
) -> list[Path] | None:
    """Sort pathing based on config entries (i.e. a list)."""
    if config_files is None:
        return None
    # Remove entries with no files and get the names of the remaining ones
    p = [item.file for item in config_files]
    return p
