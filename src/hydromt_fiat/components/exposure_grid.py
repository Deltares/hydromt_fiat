"""The custom hazard component."""

import logging
from pathlib import Path

from hydromt.model import Model
from hydromt.model.components import GridComponent
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.errors import MissingRegionError

__all__ = ["ExposureGridComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class ExposureGridComponent(GridComponent):
    """Custom exposure grid component.

    Inherits from the HydroMT-core GridComponent model-component.

    Parameters
    ----------
    model: Model
        HydroMT model instance
    filename: str
        The path to use for reading and writing of component data by default.
        By default "exposure/spatial.nc".
    region_component: str, optional
        The name of the region component to use as reference
        for this component's region. If None, the region will be set to the grid extent.
        Note that the create method only works if the region_component is None.
        For add_data_from_* methods, the other region_component should be
        a reference to another grid component for correct reprojection, by default None
    region_filename: str
        The path to use for reading and writing of the region data by default.
        By default "region.geojson".
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: str = "exposure/spatial.nc",
        region_component: str | None = None,
        region_filename: str = "region.geojson",
    ):
        super().__init__(
            model,
            filename=filename,
            region_component=region_component,
            region_filename=region_filename,
        )

    @hydromt_step
    def setup_exposure_grid(
        self,
        exposure_grid_fnames: str | Path | list[str | Path],
        exposure_grid_link_fname: str | Path,
    ) -> None:
        """Set up an exposure grid.

        Parameters
        ----------
        exposure_grid_fnames : str | Path | list[str  |  Path]
            Name of or path to exposure file(s)
        exposure_grid_link_fname : str | Path
            Table containing the names of the exposure files and corresponding
            vulnerability curves.
        """
        logger.info("Setting up exposure grid")

        if self.model.vulnerability_data.data == {}:
            raise RuntimeError(
                "setup_vulnerability step is required before setting up exposure grid."
            )
        if self.model.region is None:
            raise MissingRegionError("Region is required for setting up exposure grid.")

        # Check if linking_table exists
        if not Path(exposure_grid_link_fname).exists():
            raise ValueError("Given path to linking table does not exist.")
        # Read linking table
        exposure_linking = self.model.data_catalog.get_dataframe(
            exposure_grid_link_fname
        )

        # Check if linking table columns are named according to convention
        for col_name in ["type", "curve_id"]:
            if col_name not in exposure_linking.columns:
                raise ValueError(
                    f"Missing column, '{col_name}' in exposure grid linking table"
                )

        exposure_files = (
            [exposure_grid_fnames]
            if not isinstance(exposure_grid_fnames, list)
            else exposure_grid_fnames
        )

        # Read exposure data files from data catalog
        exposure_data = {}
        for exposure_file in exposure_files:
            exposure_fn = Path(exposure_file).stem
            da = self.model.data_catalog.get_rasterdataset(
                exposure_file,
                geom=self.model.region,
            )
            exposure_data[exposure_fn] = da

        # Get grid like from existing exposure data if there is any
        grid_like = self.data if self.data != {} else None

        # Execute the workflow function
        ds = workflows.exposure_grid_data(
            grid_like=grid_like,
            exposure_data=exposure_data,
            exposure_linking=exposure_linking,
        )

        # Set the dataset
        self.set(ds)

        # Set the config entries
        if len(self.data.data_vars) > 1:
            self.model.config.set("exposure.grid.settings.var_as_band", True)
        self.model.config.set("exposure.grid.file", self._filename)
