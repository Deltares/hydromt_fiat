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
    VALUE,
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
    def create_categorized(
        self,
        exposure_fname: Path | str,
        *,
        exposure_name: str | None = None,
        read_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Create categorized gridded exposure data.

        The data is 'measured' against the available vulnerability curves that match
        the categories in the exposure data.

        Parameters
        ----------
        exposure_fname : Path | str
            The name of (or path to) the exposure data to be setup. The data should
            consist of integer based categories that (idealy) match the entries in the
            vulnerability data.
        exposure_name : str | None, optional
            The name of the variable that the data will have in the dataset.
            If not provided the name is inferred from the stem of `expousre_fname`.
            By default None.
        read_kwargs : dict[str, Any] | None, optional
            Optional keyword arguments for reading the `exposure_fname` data.
            These arguments are passed to the HydroMT
            :py:meth:`~hydromt.DataCatalog.get_rasterdataset` method. By default None.
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
        exposure_grid = workflows.exposure_grid_categorized_setup(
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
    def create_categorized_values(
        self,
        exposure_name: str,
        *,
        exposure_table_fname: Path | str | None = None,
        exposure_table: dict[int, float | int] | None = None,
        default: float | int = 100,
        unit: str = "m**2",
        read_kwargs: dict[str, Any] | None = None,
        **select,
    ) -> None:
        """Create linked values to the categorized gridded exposure data.

        This is specific to on of the variables present the exposure data.
        A coordinates and (a) variable(s) are created that link to the values in the
        exposure data variable in terms of values and name.

        Parameters
        ----------
        exposure_name : str
            The name of the variable in the gridded exposure data to setup the
            values for.
        exposure_table_fname : Path | str | None, optional
            Table containing the values of the categories corresponding with the values
            in the exposure data. Multiple columns are accepted and then added to the
            resulting dataset. If not provided, the default value will be used for all
            categories. By default None.
        exposure_table : dict[int, float  |  int] | None, optional
            As an alternative to `exposure_table_fname`, a direct mapping (dictionary)
            of the categories to their values can be provided. The keys will be the
            categories and their values.. the values. By default None.
        default : float | int, optional
            The default value when the table is not provided or has missing values
            compared to the categorized exposure data, by default 100.
        unit : str, optional
            The unit (per) of the values, if not the standard (e.g. m**2) the values
            are translated to the standard unit of that category
            (e.g. m**2 for length squared). By default "m**2".
        read_kwargs : dict[str, Any] | None, optional
            Optional keyword arguments for reading the `exposure_table_fname` data.
            These arguments are passed to the HydroMT
            :py:meth:`~hydromt.DataCatalog.get_dataframe` method. By default None.
        """
        logger.info("Setting up table values for tabled based exposure grid")
        # Assert the variable is present
        self._assert_entry(exposure_name)

        # Get the exposure table from the data catalog, or from input
        if exposure_table_fname is not None:
            exposure_table = exposure_table or self.model.data_catalog.get_dataframe(
                exposure_table_fname,
                **(read_kwargs or {}),
            )

        # Process the input
        if exposure_table is not None:
            exposure_table = workflows.process_table(
                table=exposure_table,
                column_name=VALUE,
                index_name=exposure_name,
                **select,
            )

        # Call the workflow function
        exposure_grid_table = workflows.exposure_grid_category_values(
            exposure_data=self.data[exposure_name],
            table=exposure_table,
            unit=unit,
            default=default,
        )

        # Set the data
        self.set(exposure_grid_table)
