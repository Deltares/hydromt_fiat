"""Component utilities."""

from pathlib import Path

from hydromt.model.components import ConfigComponent


def config_file_entry(
    cfg: ConfigComponent,
    entry: str,
):
    """.

    Parameters
    ----------
    cfg : ConfigComponent
        _description_
    entry : str
        _description_
    """
    # Return None if None
    if cfg is None:
        return
    value = cfg.get_value(entry)
    # Return None if None
    if value is None:
        return
    # File check
    if Path(cfg.model.root, value).is_file():
        return value
    return
