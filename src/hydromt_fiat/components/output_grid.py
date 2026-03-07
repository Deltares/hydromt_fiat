"""Output grid component."""

import logging
from pathlib import Path

from hydromt.model import Model
from hydromt.readers import open_nc

from hydromt_fiat.components.grid import GridComponent
from hydromt_fiat.utils import EXPOSURE_GRID_FILE, OUTPUT_GRID_NAME

__all__ = ["OutputGridComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class OutputGridComponent(GridComponent):
    """Model geometry results component.

    Parameters
    ----------
    model : Model
        HydroMT model instance (FIATModel).
    """

    _build = False

    def __init__(
        self,
        model: Model,
    ):
        super().__init__(
            model=model,
            region_component=None,
        )

    ## I/O Methods
    def read(
        self,
        filename: Path | str | None = None,
        **kwargs,
    ) -> None:
        """Read the model output grid.

        Parameters
        ----------
        filename : Path | str, optional
            The path to the file, by default None.
        **kwargs : dict
            Additional keyword arguments that are passed to the
            `xr.open_dataset` function.
        """
        # Assert the mode
        self.root._assert_read_mode()
        self._initialize(skip_read=True)

        # Sort out the read path
        # Hierarchy: 1) signature 2) output defined 3) input derived
        config_filename = (
            self.model.config.get(OUTPUT_GRID_NAME)
            or self.model.config.get(EXPOSURE_GRID_FILE)
            or ""
        )
        filename = (
            Path(self.model.config.dir, filename) if filename is not None else None
        )
        filename = filename or (Path(config_filename).name or None)
        # If None, nothing to be read
        if filename is None:
            return
        read_path = Path(self.model.config.output_dir, filename)

        # Return if the path is not found
        if not read_path.is_file():
            return

        # Read the data
        logger.info(f"Reading the hazard file at {read_path.as_posix()}")
        # Read with the (old) read function from hydromt-core
        ds = open_nc(
            read_path,
            **kwargs,
        )
        # Set the data
        self.set(ds)

    def write(self) -> None:
        """Write method."""
        raise NotImplementedError(
            f"Writing not available for {self.__class__.__name__}",
        )
