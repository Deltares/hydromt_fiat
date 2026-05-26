"""Output geometry component."""

import logging
from pathlib import Path
from typing import cast

import geopandas as gpd
from hydromt.gis.vector import _filter_gdf
from hydromt.model import Model
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.components.geom import GeomsComponent
from hydromt_fiat.components.utils import (
    ensure_path_listing,
    pathing_config,
    pathing_expand,
)
from hydromt_fiat.gis import create_square_vector_grid
from hydromt_fiat.utils import EXPOSURE_GEOM_FILE, OUTPUT_GEOM_NAME, POST

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
        self._filename: str = f"{POST}/{{name}}.fgb"
        self._processed_data: dict[str, gpd.GeoDataFrame] | None = None
        super().__init__(
            model,
            region_component=None,
        )

    ## Private methods
    def _assert_output_entry(self, name: str):
        if name not in self.combined_data or not isinstance(
            self.combined_data[name], (gpd.GeoDataFrame, gpd.GeoSeries)
        ):
            raise RuntimeError(
                f"Chose from already present geometries: \
{list(self.combined_data.keys())} i.e. a GeoDataFrame or run the appropriate `setup` \
method with '{name}' as input"
            )

    def _initialize(self, skip_read=False):
        if self._processed_data is None:
            self._processed_data = {}
        return super()._initialize(skip_read)

    def _set(
        self,
        data: gpd.GeoDataFrame,
        name: str,
    ):
        """Set post processed data in the corresponding dictionary.

        Parameters
        ----------
        data : gpd.GeoDataFrame
            New post processed geometry data to add.
        name : str
            Geometry name.
        """
        self._initialize(skip_read=True)
        assert self._processed_data is not None
        if name in self._processed_data and id(self._processed_data.get(name)) != id(
            data
        ):
            logger.warning(f"Replacing post processed geometry data: {name}")

        if "fid" in data.columns:
            logger.warning(
                f"'fid' column encountered in {name}, \
column will be removed"
            )
            data.drop("fid", axis=1, inplace=True)

        # Set the data
        self._processed_data[name] = data

    ## Properties
    @property
    def combined_data(self) -> dict[str, gpd.GeoDataFrame]:
        """Return the combined output and post processed data."""
        data = dict(self.data)
        # Update with post processed data
        data.update(self.processed_data)
        # Return the combined data
        return data

    @property
    def processed_data(self) -> dict[str, gpd.GeoDataFrame]:
        """Return the post processed data."""
        if self._processed_data is None:
            self._initialize(skip_read=True)
        assert self._processed_data is not None
        return self._processed_data

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

    def write(
        self,
        **kwargs,
    ):
        """Write the post processed datasets.

        These will be placed in the 'post' directory next to the settings file (if
        it exists) or in the root directory of the model.

        Parameters
        ----------
        **kwargs : dict
            Additional keyword arguments that are passed to the
            `geopandas.to_file` function.
        """
        # If no data to write, return
        if len(self.processed_data) == 0:
            logger.info("No post processed data found, skip writing.")
            return

        # Ensure the format (also for future signature update)
        filename = Path(self._filename).as_posix()
        # Loop over the post processed data
        for name, gdf in self.processed_data.items():
            # Create the write path
            write_path = Path(
                self.root.path,
                filename.format(name=name),
            )
            # Ensure the directory
            write_dir = write_path.parent
            write_dir.mkdir(parents=True, exist_ok=True)

            logger.info(
                f"Writing the '{name}' post processed geometry data to \
{write_path.as_posix()}",
            )
            # Write the entire thing to vector file
            gdf.to_file(write_path, **kwargs)

    ## Post processing methods
    @hydromt_step
    def spatial_aggregate(
        self,
        output_name: str,
        aggregation_areas_fname: str,
        *,
        method: str = "mean",
        areal_mean: bool = False,
        per_area: bool = False,
        name: str | None = None,
    ):
        """Aggregate data spatially.

        Parameters
        ----------
        output_name : str
            The name of the dataset in the data of the component, this can either be raw
            FIAT model output data or already processed data in the `processed`
            data attribute.
        aggregation_areas_fname : str
            The dataset with areas over which to aggregate the data.
        method : str, optional
            The method of aggregation, by default "mean".
        areal_mean : bool, optional
            Whether or not to calculate the results per unit area (i.e. m2). Setting
            this to True is only recommended when `method` is set to 'sum'.
            By default False.
        per_area : bool, optional
            Whether or not to calculate per unit area using the aggregation area (True)
            or the combined (based on method) area of the features in the `output_data`.
            By default False.
        name : str, optional
            The name of the new post processed dataset in the `processed` attribute.
            If not provided, 'output_name' is used with the 'sp_aggr' suffix.
            By default None.
        """
        # Check the output_name's existence
        self._assert_output_entry(output_name)

        logger.info(
            f"Spatial aggregate of {output_name} over a provided dataset \
using the '{method}' aggregation method"
        )
        # Get the aggregation area from the data catalog
        aggregation_areas = self.data_catalog.get_geodataframe(
            data_like=aggregation_areas_fname,
        )
        # Call the workflow methods
        output_data = workflows.prep_data_for_aggregation(
            output_data=self.combined_data[output_name],
        )
        # Aggregation
        aggregated_data = workflows.aggregate_spatially(
            output_data=output_data,
            aggregation_areas=aggregation_areas.to_crs(output_data.crs),
            method=method,
            areal_mean=areal_mean,
            per_area=per_area,
        )

        # Set the data
        self._set(data=aggregated_data, name=name or f"{output_name}_sp_aggr")

    @hydromt_step
    def spatial_square_aggregate(
        self,
        output_name: str,
        *,
        res: float | int = 1,
        unit: str = "km",
        method: str = "mean",
        name: str | None = None,
    ) -> None:
        """Aggregate FIAT vector output data to a square cell grid.

        Parameters
        ----------
        output_name : str
            The name of the dataset in the data of the component, this can either be raw
            FIAT model output data or already processed data in the `processed`
            data attribute.
        res : float | int
            The resolution of the resulting vector grid. By default 1.
        unit : str, optional
            The unit of the res variables. By default 'km'.
        method : str, optional
            The method of aggregation, by default "mean".
        name : str, optional
            The name of the new post processed dataset in the `processed` attribute.
            If not provided, 'output_name' is used with the 'sq_aggr' suffix.
            By default None.
        """
        # Check the output_name's existence
        self._assert_output_entry(output_name)

        logger.info(
            f"Spatial square aggregate of {output_name} at {res} {unit} resolution \
using the '{method}' aggregation method"
        )
        # Prep the output data
        output_data = workflows.prep_data_for_aggregation(
            output_data=self.combined_data[output_name],
        )

        # Create a square vector grid
        aggregation_areas = create_square_vector_grid(
            bbox=output_data.total_bounds,
            crs=output_data.crs,
            res=res,
            unit=unit,
        )

        # Call the aggregation function
        aggregated_data = workflows.aggregate_spatially(
            output_data=output_data,
            aggregation_areas=aggregation_areas,
            method=method,
        )

        # Clip based on the region
        aggregated_data = aggregated_data.iloc[
            _filter_gdf(
                aggregated_data,
                geom=self.model.region,
                bbox=aggregated_data.total_bounds,
            ),
            :,
        ]

        # Set the data
        self._set(data=aggregated_data, name=name or f"{output_name}_sq_aggr")
