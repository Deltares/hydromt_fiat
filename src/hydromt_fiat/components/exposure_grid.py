"""The custom exposure grid component."""

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
    model : Model
        HydroMT model instance
    filename : str
        The path to use for reading and writing of component data by default.
        By default "exposure/spatial.nc".
    region_component : str, optional
        The name of the region component to use as reference
        for this component's region. If None, the region will be set to the grid extent.
        Note that the create method only works if the region_component is None.
        For add_data_from_* methods, the other region_component should be
        a reference to another grid component for correct reprojection, by default None
    region_filename : str
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

    ## I/O methods
    @hydromt_step
    def read(
        self,
        filename: str | None = None,
        **kwargs,
    ):
        """Read the exposure grid data.

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root, by default 'exposure/spatial.nc'
        **kwargs : dict
            Additional keyword arguments to be passed to the `read_nc` method.
        """
        # Sort the filename
        # Hierarchy: 1) signature, 2) config file, 3) default
        filename = (
            filename
            or self.model.config.get("exposure.grid.file", abs_path=True)
            or self._filename
        )
        # Read the data
        logger.info("Reading the exposure grid data..")
        super().read(filename=filename, **kwargs)

    @hydromt_step
    def write(
        self,
        filename: str | None = None,
        **kwargs,
    ):
        """Write the exposure grid data.

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root, by default 'exposure/spatial.nc'
        **kwargs : dict
            Additional keyword arguments to be passed to the `write_nc` method.
        """
        # Sort out the filename
        # Hierarchy: 1) signature, 2) config file, 3) default
        filename = (
            filename or self.model.config.get("exposure.grid.file") or self._filename
        )
        write_path = Path(self.root.path, filename)

        # Update the kwargs
        if "gdal_compliant" not in kwargs:
            kwargs["gdal_compliant"] = True
        # Write it in a gdal compliant manner by default
        logger.info("Writing the exposure grid data..")
        super().write(write_path.as_posix(), **kwargs)

        # Update the config
        self.model.config.set("exposure.grid.file", write_path)

    ## Mutating methods
    @hydromt_step
    def setup(
        self,
        exposure_fnames: Path | str | list[Path | str],
        exposure_link_fname: Path | str,
    ) -> None:
        """Set up an exposure grid.

        Parameters
        ----------
        exposure_fnames : Path | str | list[Path | str]
            Name of or path to exposure file(s)
        exposure_link_fname : Path | str
            Table containing the names of the exposure files and corresponding
            vulnerability curves.
        """
        logger.info("Setting up gridded exposure")

        if self.model.vulnerability.data.identifiers.empty == True:
            raise RuntimeError(
                "'setup_vulnerability' step is required \
before setting up exposure grid"
            )
        if self.model.region is None:
            raise MissingRegionError("Region is required for setting up exposure grid")

        # Read linking table
        exposure_linking = self.model.data_catalog.get_dataframe(exposure_link_fname)

        # Sort the input out as iterator
        exposure_fnames = (
            [exposure_fnames]
            if not isinstance(exposure_fnames, list)
            else exposure_fnames
        )

        # Read exposure data files from data catalog
        exposure_data = {}
        for fname in exposure_fnames:
            name = Path(fname).stem
            da = self.model.data_catalog.get_rasterdataset(
                fname,
                geom=self.model.region,
            )
            exposure_data[name] = da

        # Get grid like from existing exposure data if there is any
        grid_like = self.data if self.data else None

        # Execute the workflow function
        ds = workflows.exposure_grid_setup(
            grid_like=grid_like,
            exposure_data=exposure_data,
            exposure_linking=exposure_linking,
            vulnerability=self.model.vulnerability.data.identifiers,
        )

        # Set the dataset
        self.set(ds)

        # Set the config entries
        self.model.config.set("exposure.grid.settings.var_as_band", False)
        if len(self.data.data_vars) > 1:
            self.model.config.set("exposure.grid.settings.var_as_band", True)
