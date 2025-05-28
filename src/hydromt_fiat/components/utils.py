"""Component utilities."""

from pathlib import Path

from hydromt.model.components import ConfigComponent


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
