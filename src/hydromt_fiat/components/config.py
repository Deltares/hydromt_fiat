"""The config component."""

import logging
from pathlib import Path

from hydromt.model import Model
from hydromt.model.components import ModelComponent
from hydromt.model.steps import hydromt_step

from hydromt_fiat.readers import read_config
from hydromt_fiat.settings import DEFAULT_SETTINGS, Settings
from hydromt_fiat.settings.file import FileContext
from hydromt_fiat.utils import SETTINGS
from hydromt_fiat.writers import write_config

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

    _build = True

    def __init__(
        self,
        model: Model,
        *,
        filename: Path | str = f"{SETTINGS}.toml",
    ):
        self._data: Settings | None = None
        self._filename: Path | str = filename
        super().__init__(
            model,
        )

    ## Private methods
    def _initialize(
        self,
        skip_read: bool = False,
    ) -> None:
        """Initialize the model config."""
        if self._data is None:
            self._data = Settings()
            if not skip_read and self.root.is_reading_mode():
                self.read()

    ## Properties
    @property
    def context(self) -> FileContext:
        """Return the context for the pydantic config."""
        return FileContext(config_dir=self.dir, output_dir=self.output_dir)

    @property
    def data(self) -> Settings:
        """Model config values."""
        if self._data is None:
            self._initialize()
        assert isinstance(self._data, Settings)
        return self._data

    @property
    def dir(self) -> Path:
        """The absolute directory path of configurations file.

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

    @property
    def output_dir(self) -> Path:
        """The absolute path of the output directory.

        The value is based on `ConfigComponent.dir`.
        """
        return self.dir / self.data.output.path

    @output_dir.setter
    def output_dir(self, value: Path | str):
        """Set the output directory."""
        self.data.output.path = Path(value)

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
        logger.info("Reading model configuration")
        data = read_config(read_path=read_path)
        self._data = Settings.model_validate(data, context=self.context)

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

        # Path from signature or internal default
        # Hierarchy is 1) signature, 2) default
        p = filename or self._filename

        # Set the write path
        write_path = Path(self.root.path, p)

        # Solve the pathing in the data
        # Extra check for dir_input
        write_data = self.data.to_dict(context=self.context)

        # Dump to a file
        logger.info("Writing model configuration")
        if self.data == DEFAULT_SETTINGS:
            logger.warning(
                "No alterations were made to the default settings, writing default",
            )
        write_config(data=write_data, write_path=write_path)

    ## Mutating methods
    @hydromt_step
    def clear(self) -> None:
        """Clear the config data."""
        self._data = None
        self._initialize(skip_read=True)

    @hydromt_step
    def update(self, **settings) -> None:
        """Update the configuration settings.

        Parameters
        ----------
        settings : dict[str, Any]
            Settigns to up update the configuration with.
        """
        self._data = Settings.model_validate(
            {**self.data.to_dict(), **settings},
            context=self.context,
        )
