"""Output geometry component."""

import logging
from pathlib import Path
from typing import cast

import geopandas as gpd
from hydromt.model import Model
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.components.geom import GeomsComponent
from hydromt_fiat.components.utils import (
    ensure_path_listing,
    pathing_config,
    pathing_expand,
)
from hydromt_fiat.utils import EXPOSURE_GEOM_FILE, OUTPUT_GEOM_NAME

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
        **kwargs,
    ) -> None:
        """Read the model output geometries.

        Parameters
        ----------
        filename : str, optional
            The path to a FIAT model output vector file, by default None.
        **kwargs : dict
            Additional keyword arguments that are passed to the
            `geopandas.read_file` function.
        """
        self.root._assert_read_mode()
        self._initialize(skip_read=True)

        # Sort out the pathing
        # Hierarchy: 1) signature 2) settings
        # Sort the signature first
        files = pathing_expand(self.model.config.dir, filename)

        # Look at the in and outputs of the config file
        infiles = (
            ensure_path_listing(
                self.model.config.get(EXPOSURE_GEOM_FILE),
            )
            or []
        )
        infiles = [
            Path(self.model.config.output_dir, item.name).with_suffix(".gpkg")
            for item in infiles
        ]
        # Get the directly specified output files
        outfiles = ensure_path_listing(
            self.model.config.get(
                OUTPUT_GEOM_NAME,
                abs_path=True,
                root=self.model.config.output_dir,
            )
        )
        # Supplement the defined output with input (names are the same in that case)
        if outfiles is None:
            outfiles = infiles
        outfiles += infiles[len(outfiles) :]

        # Set the files
        files = files or pathing_config(outfiles)
        if files is None:
            return

        # Read the output data
        logger.info("Reading model geometry outputs")
        for read_path, name in zip(*files):
            # If file doesn't exist, skip it
            if not read_path.is_file():
                continue
            logger.info(f"Reading the {name} output file at {read_path.as_posix()}")
            # Read the data and set it
            data = cast(gpd.GeoDataFrame, gpd.read_file(read_path, **kwargs))
            self.set(data=data, name=name)

    def write(self):
        """Write method."""
        raise NotImplementedError(
            f"Writing not available for {self.__class__.__name__}",
        )

    ## Post processing methods
    @hydromt_step
    def aggregate_square(
        self,
        output_name: str,
        res: float | int = 1,
        method: str = "mean",
        output_dir: Path | str | None = None,
    ) -> None:
        """Aggregate FIAT vector output data to a square cell grid.

        Parameters
        ----------
        output_name : str
            The name of the dataset in the data of the component.
        res : float | int
            The resolution of the resulting vector grid in km. By default 1.
        method : str, optional
            The method of aggregation, by default "mean".
        output_dir : Path | str | None, optional
            The output directory. If None, the data is written to the 'aggregated'
            directory next to the configurations file. By default None.
        """
        # Check the output_name's existence
        if output_name not in self.data:
            raise ValueError(f"'{output_name}' not in the output component's data")

        logger.info(
            f"Square aggregate of {output_name} at {res} km resolution \
using the '{method}' aggregation method"
        )
        # Call the workflow function
        vector_grid = workflows.aggregate_vector_grid(
            output_data=self.data[output_name],
            res=res,
            method=method,
            region=self.model.region,
        )

        # Check the output directory
        output_dir = output_dir or "aggregate"
        output_dir = Path(self.model.config.dir, output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write the data
        out_fname = f"{output_name}_sq_aggr.fgb"
        logger.info(f"Writing aggregate file {out_fname} to {output_dir.as_posix()}")
        vector_grid.to_file(Path(output_dir, out_fname))
