"""Output grid component."""

import logging
from pathlib import Path

import xarray as xr
from hydromt.model import Model
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.components.grid import GridComponent
from hydromt_fiat.readers import read_grid
from hydromt_fiat.settings import get_file_from_settings_component
from hydromt_fiat.utils import GRID, POST

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
        self._filename: str = f"{POST}/{{name}}.nc"
        self._processed_data: dict[str, xr.DataArray] | None = None
        super().__init__(
            model=model,
            region_component=None,
        )

    ## Private methods
    def _initialize(self, skip_read=False):
        if self._processed_data is None:
            self._processed_data = {}
        return super()._initialize(skip_read)

    def _set(
        self,
        data: xr.DataArray | xr.Dataset,
        name: str,
    ):
        """Set post processed data.

        Parameters
        ----------
        data : xr.DataArray
            The data to add.
        name : str
            The name of the data in the data dictionary.
        """
        self._initialize(skip_read=True)
        assert self._processed_data is not None
        if name in self._processed_data and id(self._processed_data.get(name)) != id(
            data
        ):
            logger.warning(f"Replacing post processed grid data: {name}")
        self._processed_data[name] = data

    ## Properties
    @property
    def processed_data(self) -> dict[str, xr.DataArray]:
        """Return the post processed data."""
        if self._processed_data is None:
            self._initialize(skip_read=True)
        assert self._processed_data is not None
        return self._processed_data

    ## I/O Methods
    @hydromt_step
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
        if not self.model._assert_model_type(GRID, error=False):
            return
        # Assert the mode
        self.root._assert_read_mode()
        self._initialize(skip_read=True)

        # Sort out the read path
        # Hierarchy: 1) signature 2) output defined 3) input derived
        config_filename = (
            get_file_from_settings_component(self.model.config.data.output)
            or get_file_from_settings_component(self.model.config.data.exposure)
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
        logger.info("Reading model output grid data")
        ds = read_grid(read_path=read_path, **kwargs)
        # Set the data
        self.set(ds)

    def write(self) -> None:
        """Write method."""
        raise NotImplementedError(
            f"Writing not available for {self.__class__.__name__}",
        )

    @hydromt_step
    def spatial_aggregate(
        self,
        output_name: str,
        res: float | int,
        method: str = "average",
        align: bool = False,
        name: str | None = None,
    ) -> None:
        """Aggregate gridded output data to a coarser resolution.

        Parameters
        ----------
        output_name : str
            The name of the data variables in the FIAT model output data.
        res : float | int
            The resolution of the aggregated data. The resolution is required to be
            bigger than the resolution of the provided data.
        method : str, optional
            The aggregation method, by default "average".
        align : bool, optional
            Whether to align the target transform to the resolution. By default False.
        name : str, optional
            The name of the data entry in the post processed data dictionary.
            If not provided, `output_name` is used with '_aggr_<`res`>' as suffix.
            By default None.
        """
        self.model._assert_model_type(GRID)
        # Assert the model entry
        self._assert_entry(name=output_name, spatial=True)

        # Call the workflow function
        aggregated = workflows.aggregate_grid(
            output_data=self.data[output_name],
            res=res,
            method=method,
            align=align,
        )

        self._set(aggregated, name=name or output_name + f"_aggr_{res}")
