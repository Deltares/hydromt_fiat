"""Output geometry component."""

import logging

from hydromt.model import Model
from hydromt.model.steps import hydromt_step

from hydromt_fiat.components.geom import GeomsComponent

__all__ = ["OutputGeomsComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class OutputGeomsComponent(GeomsComponent):
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
            model,
            region_component=None,
        )

    ## I/O methods
    @hydromt_step
    def read(
        self,
        filename: str | None = None,
    ) -> None:
        """Read the model output geometries.

        Parameters
        ----------
        filename : str, optional
            The path to the file, by default None
        """
        logger.info("Reading model geometry outputs.")
        filename = filename or self.model.config.get("output.geom.name")
        if filename is None:
            return

    def write(self):
        """Write method."""
        raise NotImplementedError("")

    @hydromt_step
    def aggregate_grid(
        self,
        name: str,
        res: float | int,
    ):
        """_summary_.

        Parameters
        ----------
        name : str
            _description_
        res : float | int
            _description_
        """
        pass
