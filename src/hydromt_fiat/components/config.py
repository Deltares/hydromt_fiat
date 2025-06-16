"""The custum config component."""

import logging
from pathlib import Path

from hydromt._io import _write_toml
from hydromt.model import Model
from hydromt.model.components import ConfigComponent
from hydromt.model.steps import hydromt_step

from hydromt_fiat.components.utils import make_config_paths_relative

__all__ = ["FIATConfigComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class FIATConfigComponent(ConfigComponent):
    """A Custom config component for FIAT models.

    Parameters
    ----------
    model : Model
        HydroMT model instance
    filename : str
        A path relative to the root where the configuration file will
        be read and written if user does not provide a path themselves.
        By default 'config.yml'
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: str = "settings.toml",
    ):
        super().__init__(
            model,
            filename=filename,
        )

    ## I/O methods
    @hydromt_step
    def read(
        self,
        filename: Path | str | None = None,
    ):
        """Read the FIAT model config file.

        Parameters
        ----------
        filename : Path | str, optional
            The path to the model configurations file. This can either be a relative
            or absolute path. If not provided, the component attribute `_filename` is
            used as a fallback. By default None.
        """
        # Just supercharge, but change argument to align with other components.
        super().read(filename)

    @hydromt_step
    def write(
        self,
        filename: Path | str | None = None,
    ):
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
            logger.warning("No data in config component, skip writing")
            return

        logger.info("Writing the config file..")
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
        _write_toml(write_path, write_data)
