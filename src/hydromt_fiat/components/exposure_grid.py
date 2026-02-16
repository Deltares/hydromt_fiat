"""The exposure grid component."""

import logging
from pathlib import Path

from hydromt.model import Model
from hydromt.model.steps import hydromt_step
from hydromt.readers import open_nc
from hydromt.writers import write_nc

from hydromt_fiat import workflows
from hydromt_fiat.components.grid import GridComponent
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.gis.raster_utils import force_ns
from hydromt_fiat.gis.utils import crs_representation
from hydromt_fiat.utils import (
    EXPOSURE,
    EXPOSURE_GRID_FILE,
    EXPOSURE_GRID_SETTINGS,
    GRID,
    MODEL_TYPE,
    SRS,
    VAR_AS_BAND,
)

__all__ = ["ExposureGridComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class ExposureGridComponent(GridComponent):
    """Exposure grid component.

    Inherits from the HydroMT-core GridComponent model-component.

    Parameters
    ----------
    model : Model
        HydroMT model instance (FIATModel).
    filename : str, optional
        The path to use for reading and writing of component data by default.
        By default "exposure/spatial.nc".
    region_component : str, optional
        The name of the region component to use as reference
        for this component's region. If None, the region will be set to the grid extent.
        Note that the create method only works if the region_component is None.
        For add_data_from_* methods, the other region_component should be
        a reference to another grid component for correct reprojection, by default None.
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: str = f"{EXPOSURE}/spatial.nc",
        region_component: str | None = None,
    ):
        self._filename = filename
        super().__init__(
            model,
            region_component=region_component,
        )

    ## I/O methods
    @hydromt_step
    def read(
        self,
        filename: Path | str | None = None,
        **kwargs,
    ) -> None:
        """Read the exposure grid data.

        Parameters
        ----------
        filename : Path | str, optional
            Filename relative to model root. If None, the value is either taken from
            the model configurations or the `_filename` attribute, by default None.
        **kwargs : dict
            Additional keyword arguments to be passed to the `open_dataset` function
            from xarray.
        """
        # Check the state
        self.root._assert_read_mode()
        self._initialize(skip_read=True)

        # Sort the filename
        # Hierarchy: 1) signature, 2) config file, 3) default
        filename = (
            filename
            or self.model.config.get(EXPOSURE_GRID_FILE, abs_path=True)
            or self._filename
        )
        # Read the data
        read_path = Path(self.root.path, filename)
        # Return on nothing found
        if not read_path.is_file():
            return
        logger.info(f"Reading the exposure grid file at {read_path.as_posix()}")
        # Read with the (old) read function from hydromt-core
        ds = open_nc(
            read_path,
            **kwargs,
        )
        # Set the dataset
        self.set(ds)

    @hydromt_step
    def write(
        self,
        filename: Path | str | None = None,
        gdal_compliant: bool = True,
        **kwargs,
    ) -> None:
        """Write the exposure grid data.

        Parameters
        ----------
        filename : Path | str, optional
            Filename relative to model root. If None, the value is either taken from
            the model configurations or the `_filename` attribute, by default None.
        gdal_compliant : bool, optional
            If True, write grid data in a way that is compatible with GDAL,
            by default True.
        **kwargs : dict
            Additional keyword arguments to be passed to the `to_netcdf` method from
            xarray.
        """
        # Check the state
        self.root._assert_write_mode()

        # Check for data. If no data, warn and return
        if len(self.data) == 0:
            logger.info("No exposure grid data found, skip writing.")
            return

        # Sort out the filename
        # Hierarchy: 1) signature, 2) config file, 3) default
        filename = (
            filename or self.model.config.get(EXPOSURE_GRID_FILE) or self._filename
        )
        write_path = Path(self.root.path, filename)

        # Write it in a gdal compliant manner by default
        logger.info(f"Writing the exposure grid data to {write_path.as_posix()}")
        # Force north south before writing
        self._data = force_ns(self.data)  # type: ignore[assignment]
        write_nc(
            self.data,
            file_path=write_path,
            gdal_compliant=gdal_compliant,
            rename_dims=False,
            force_overwrite=self.root.mode.is_override_mode(),
            force_sn=False,
            progressbar=True,
            to_netcdf_kwargs=kwargs,
        )

        # Update the config
        self.model.config.set(EXPOSURE_GRID_FILE, write_path)
        # Check for multiple bands, because gdal and netcdf..
        self.model.config.set(f"{EXPOSURE_GRID_SETTINGS}.{VAR_AS_BAND}", False)
        if len(self.data.data_vars) > 1:
            self.model.config.set(f"{EXPOSURE_GRID_SETTINGS}.{VAR_AS_BAND}", True)
        # Set the srs
        self.model.config.set(
            f"{EXPOSURE_GRID_SETTINGS}.{SRS}",
            crs_representation(self.data.raster.crs),
        )

    ## Setup methods
    @hydromt_step
    def setup(
        self,
        exposure_fnames: Path | str | list[Path | str],
        exposure_link_fname: Path | str | None = None,
    ) -> None:
        """Set up an exposure grid.

        Parameters
        ----------
        exposure_fnames : Path | str | list[Path | str]
            Name of or path to exposure file(s).
        exposure_link_fname : Path | str, optional
            Table containing the names of the exposure files and corresponding
            vulnerability curves. By default None
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
        exposure_linking = None
        if exposure_link_fname is not None:
            exposure_linking = self.model.data_catalog.get_dataframe(
                exposure_link_fname,
            )

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
        logger.info("Setting the model type to 'grid'")
        self.model.config.set(MODEL_TYPE, GRID)
