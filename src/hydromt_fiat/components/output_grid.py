"""Output grid component."""

from pathlib import Path

from hydromt.model import Model

from hydromt_fiat.components.grid import GridComponent


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
    ) -> None:
        """Read the model output grid.

        Parameters
        ----------
        filename : Path | str, optional
            The path to the file, by default None.
        """
        ...

    def write(self) -> None:
        """Write method."""
        raise NotImplementedError(
            f"Writing not available for {self.__class__.__name__}",
        )
