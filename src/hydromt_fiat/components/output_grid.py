"""Output grid component."""

from hydromt.model import Model

from hydromt_fiat.components.grid import GridComponent


class OutputGridComponent(GridComponent):
    """_summary_.

    Parameters
    ----------
    model : Model
        _description_
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
