"""The config component."""

import logging
from pathlib import Path
from typing import Any, cast

import tomlkit
from hydromt._io.readers import _read_toml
from hydromt.model import Model
from hydromt.model.components import ModelComponent
from hydromt.model.steps import hydromt_step

from hydromt_fiat.components.utils import get_item, make_config_paths_relative
from hydromt_fiat.utils import SETTINGS

__all__ = ["ConfigComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class ConfigComponent(ModelComponent):
    """Config component.

    Container for all the settings of a Delft-FIAT model.

    Parameters
    ----------
    model : Model
        HydroMT model instance (FIATModel).
    filename : str, optional
        A path relative to the root where the configuration file will
        be read and written if user does not provide a path themselves.
        By default 'settings.toml'.
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: str = f"{SETTINGS}.toml",
    ):
        self._data: dict[str, Any] | None = None
        self._filename: Path | str = filename
        super().__init__(
            model,
        )

    ## Private methods
    def _initialize(self, skip_read=False) -> None:
        """Initialize the model config."""
        if self._data is None:
            self._data = {}
            if not skip_read and self.root.is_reading_mode():
                self.read()

    ## Properties
    @property
    def data(self) -> dict[str, Any]:
        """Model config values."""
        if self._data is None:
            self._initialize()
        assert isinstance(self._data, dict)
        return self._data

    @property
    def dir(self) -> Path:
        """The absolute directory of configurations file.

        In most cases this will be equal to the model root directory, however one
        can specify a subdirectory for the configuration file, therefore this property
        exists.
        """
        return Path(self.root.path, self.filename).parent

    @property
    def filename(self) -> Path | str:
        """Filename of the config file."""
        return self._filename

    @filename.setter
    def filename(self, value: Path | str):
        self._filename = value

    ## I/O methods
    @hydromt_step
    def read(
        self,
        filename: Path | str | None = None,
    ) -> None:
        """Read the FIAT model config file.

        Parameters
        ----------
        filename : Path | str, optional
            The path to the model configurations file. This can either be a relative
            or absolute path. If not provided, the component attribute `_filename` is
            used as a fallback. By default None.
        """
        self.root._assert_read_mode()
        self._initialize(skip_read=True)

        # Sort the filename
        # Hierarchy: 1) signature, 2) default
        filename = filename or self.filename
        self.filename = filename
        read_path = Path(self.root.path, filename)

        # Check for the path
        if not read_path.is_file():
            return

        # Read the data (config)
        logger.info(f"Reading the config file at {read_path.as_posix()}")
        self._data = _read_toml(read_path)

    @hydromt_step
    def write(
        self,
        filename: Path | str | None = None,
    ) -> None:
        """Write the FIAT model config file.

        Parameters
        ----------
        filename : Path | str, optional
            The path to the model configurations file. This can either be a relative
            or absolute path. If not provided, the component attribute `_filename` is
            used as a fallback. By default None.
        """
        self.root._assert_write_mode()

        # If no data, return
        if not self.data:
            logger.warning("No data in config component, writing empty file..")

        # Path from signature or internal default
        # Hierarchy is 1) signature, 2) default
        p = filename or self._filename

        # Set the write path
        write_path = Path(self.root.path, p)

        # Solve the pathing in the data
        # Extra check for dir_input
        parent_dir = write_path.parent
        write_data = make_config_paths_relative(self.data, parent_dir)

        # Write the data to the drive.
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True)

        # Dump to a file
        logger.info(f"Writing the config data to {write_path.as_posix()}")
        with open(write_path, "w") as writer:
            tomlkit.dump(write_data, writer)

    ## Action methods
    def get(
        self,
        key: str,
        fallback: Any | None = None,
        abs_path: bool = False,
    ) -> Any:
        """Get a config value at key(s).

        Parameters
        ----------
        args : tuple | str
            Key can given as a string with '.' indicating a new level: ('key1.key2').
        fallback: Any, optional
            Fallback value if key not found in config, by default None.
        abs_path: bool, optional
            If True return the absolute path relative to the configurations directory,
            by default False.

        Returns
        -------
        value : Any
            Dictionary value
        """
        parts = key.split(".")
        current = dict(self.data)  # reads config at first call
        value = get_item(
            parts, current, root=self.dir, fallback=fallback, abs_path=abs_path
        )
        # Return the value
        return value

    def set(self, key: str, value: Any) -> None:
        """Update the config dictionary at key(s) with values.

        Parameters
        ----------
        key : str
            A string with '.' indicating a new level: 'key1.key2' will translate
            to {"key1":{"key2": value}}.
        value : Any
            The value to set the config to.
        """
        self._initialize()
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                self.set(f"{key}.{subkey}", subvalue)
                return
        if value is None:  # Not allowed in toml files
            return
        parts = key.split(".")
        num_parts = len(parts)
        current = cast(dict[str, Any], self._data)
        for i, part in enumerate(parts):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            if i < num_parts - 1:
                current = current[part]
            else:
                current[part] = value

    ## Mutating methods
    @hydromt_step
    def clear(self):
        """Clear the config data."""
        self._data = None
        self._initialize(skip_read=True)
