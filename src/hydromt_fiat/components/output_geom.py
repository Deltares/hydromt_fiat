"""Output geometry component."""

import logging

from hydromt.model import Model
from hydromt.model.steps import hydromt_step

from hydromt_fiat.components.geom import GeomsCustomComponent

__all__ = ["OutputGeomsComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class OutputGeomsComponent(GeomsCustomComponent):
    """Model geometry results component.

    Parameters
    ----------
    model : Model
        HydroMT model instance (FIATModel).
    """

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
    ):
        """Read the model output geometries.

        Parameters
        ----------
        filename : str, optional
            The path to the file, by default None
        """
        logger.info("")
        filename = filename or self.model.config.get("")

    def write(self):
        """Write method."""
        raise NotImplementedError("")
