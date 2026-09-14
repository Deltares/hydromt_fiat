"""The exposure grid component."""

import logging
from pathlib import Path
from typing import Any

from hydromt.model import Model
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.components.grid import GridComponent
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.gis.raster import expand_raster_to_bounds
from hydromt_fiat.gis.utils import crs_representation
from hydromt_fiat.readers import read_grid
from hydromt_fiat.settings import get_file_from_settings_component
from hydromt_fiat.settings.exposure import ExposureGrid, ExposureGridSettings
from hydromt_fiat.utils import (
    EXPOSURE,
    GRID,
)
from hydromt_fiat.writers import write_grid

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
            or get_file_from_settings_component(self.model.config.data.exposure.grid)
            or self._filename
        )
        # Read the data
        read_path = Path(self.root.path, filename)
        # Return on nothing found
        if not read_path.is_file():
            return
        logger.info("Reading exposure grid data")
        # Read with the simple read function
        ds = read_grid(read_path=read_path, **kwargs)
        # Set the dataset
        self.set(ds)

    @hydromt_step
    def write(
        self,
        filename: Path | str | None = None,
        compress: bool = True,
        gdal_compliant: bool = True,
        **kwargs,
    ) -> None:
        """Write the exposure grid data.

        Parameters
        ----------
        filename : Path | str, optional
            Filename relative to model root. If None, the value is taken from
            the `_filename` attribute, by default None.
        compress : bool, optional
            Whether or not to compress the data, by default True.
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
        # Hierarchy: 1) signature, 2) default
        filename = filename or self._filename
        write_path = Path(self.root.path, filename)

        # Write it in a gdal compliant manner by default
        logger.info("Writing exposure grid data")
        write_grid(
            data=self.data,
            write_path=write_path,
            compress=compress,
            gdal_compliant=gdal_compliant,
            overwrite=self.root.mode.is_override_mode(),
            **kwargs,
        )

        # Update the config
        self.model.config.data.exposure.grid = ExposureGrid(
            file=write_path,
            settings=ExposureGridSettings(crs=crs_representation(self.data.raster.crs)),
        )

    ## Setup methods
    @hydromt_step
    def create(
        self,
        exposure_fnames: Path | str | list[Path | str],
        exposure_link_fname: Path | str | None = None,
        *,
        expand: bool = True,
        read_kwargs: dict[str, Any] | None = None,
        read_link_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Create an exposure grid from data sources.

        Parameters
        ----------
        exposure_fnames : Path | str | list[Path | str]
            Name of or path to exposure file(s).
        exposure_link_fname : Path | str, optional
            Table containing the names of the exposure files and corresponding
            vulnerability curves. By default None.
        expand : bool, optional
            Whether to expand the hazard data to the bounding box of the model region.
            Nothing is done when the hazard data already covers the region.
            By default True.
        read_kwargs : dict, optional
            Optional keyword arguments for reading the `exposure_fnames` data. These
            arguments are passed to the HydroMT
            :py:meth:`~hydromt.DataCatalog.get_rasterdataset` method. By default None.
        read_link_kwargs : dict, optional
            Optional keyword arguments for reading the `exposure_link_fname` data.
            These arguments are passed to the HydroMT
            :py:meth:`~hydromt.DataCatalog.get_dataframe` method. By default None.
        """
        logger.info("Setting up gridded exposure")
        # Check for the vulnerability
        if self.model.vulnerability.data.identifiers.empty:
            raise RuntimeError(
                "'vulnerability.create' step is required \
before setting up exposure grid"
            )
        if self.model.region is None:
            raise MissingRegionError("Region is required for setting up exposure grid")

        # Read linking table
        exposure_link = None
        if exposure_link_fname is not None:
            exposure_link = self.model.data_catalog.get_dataframe(
                exposure_link_fname, **(read_link_kwargs or {})
            )

        # Sort the input out as iterator
        exposure_fnames = (
            [exposure_fnames]
            if not isinstance(exposure_fnames, list)
            else exposure_fnames
        )

        # Read exposure data files from data catalog
        exposure_data = {}
        kwargs = {"buffer": 1}
        kwargs.update(read_kwargs or {})
        # Loop over the entries
        for fname in exposure_fnames:
            name = Path(fname).stem
            da = self.model.data_catalog.get_rasterdataset(
                fname,
                geom=self.model.region,
                **kwargs,
            )
            exposure_data[name] = da

        # Execute the workflow function
        ds = workflows.exposure_grid_default_setup(
            exposure_data=exposure_data,
            vulnerability=self.model.vulnerability.data.identifiers,
            grid_like=self.like,
            exposure_link=exposure_link,
        )

        # Expand if necessary
        if self.model.region is not None and ds.raster.crs is not None and expand:
            ds = expand_raster_to_bounds(
                ds=ds,
                bbox=self.model.region.to_crs(da.raster.crs).total_bounds,
            )

        # Set the dataset
        self.set(ds)

        # Set the config entries
        logger.info("Setting the model type to 'grid'")
        self.model.config.data.model.type = GRID

    @hydromt_step
    def create_table_based(
        self,
        exposure_fname: Path | str,
        *,
        exposure_name: str | None = None,
        read_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """_summary_.

        Parameters
        ----------
        exposure_fname : Path | str
            _description_
        exposure_name : str | None, optional
            _description_, by default None
        read_kwargs : dict[str, Any] | None, optional
            _description_, by default None

        Raises
        ------
        RuntimeError
            _description_
        """
        logger.info("Setting up gridded value-table based exposure")
        # Check for the vulnerability data
        if self.model.vulnerability.data.identifiers.empty:
            raise RuntimeError(
                "'vulnerability.create' step is required \
before setting up exposure grid"
            )
        if self.model.region is None:
            raise MissingRegionError("Region is required for setting up exposure grid")

        # Read the exposure data
        kwargs = {"buffer": 1}
        kwargs.update(read_kwargs or {})
        exposure_data = self.data_catalog.get_rasterdataset(
            exposure_fname,
            geom=self.model.region,
            **kwargs,
        )

        # Execute the workflow function
        exposure_grid = workflows.exposure_grid_table_based_setup(
            exposure_data=exposure_data,
            vulnerability=self.model.vulnerability.data.identifiers,
            name=(exposure_name or Path(exposure_fname).stem),
            grid_like=self.like,
        )

        # Set the data
        self.set(exposure_grid)

        # Set the config entries
        logger.info("Setting the model type to 'grid'")
        self.model.config.data.model.type = GRID

    @hydromt_step
    def create_table_values(
        self,
        exposure_name: str,
        *,
        table_fname: Path | str | None = None,
        table: dict[int, float | int] | None = None,
        default: float | int = 100,
        read_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """_summary_.

        Parameters
        ----------
        exposure_name : str
            _description_
        table_fname : Path | str | None, optional
            _description_, by default None
        table : dict[int, float  |  int] | None, optional
            _description_, by default None
        default : float | int, optional
            _description_, by default 100
        read_kwargs : dict[str, Any] | None, optional
            _description_, by default None
        """
        # Assert the variable is present
        self._assert_entry(exposure_name)

        # Call the workflow function
        exposure_table = workflows.exposure_grid_table_values(
            exposure_data=self.data[exposure_name],
            values=table,
            default=default,
        )

        # Set the data
        self.set(exposure_table)
