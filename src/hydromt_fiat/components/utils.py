"""Component utilities."""

from pathlib import Path

from hydromt._utils.naming_convention import _expand_uri_placeholders


def expand_path_wildcards(
    root: Path, filename: Path | str | None = None
) -> list[Path] | None:
    """Sort the pathing on reading based on a wildcard."""
    # If the filename is None, do nothing
    if filename is None:
        return None
    # Expand
    filename = Path(filename).as_posix()
    path_glob, _, _ = _expand_uri_placeholders(filename)
    p = list(Path(root).glob(path_glob))
    # Get the unique names
    return p
