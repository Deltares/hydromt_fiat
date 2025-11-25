"""The exposure grid component."""

import logging
from pathlib import Path

import geopandas as gpd
import xarray as xr
from hydromt._io.readers import _read_nc
from hydromt._io.writers import _write_nc
from hydromt.model import Model
from hydromt.model.components import GridComponent
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.gis.raster_utils import force_ns
from hydromt_fiat.gis.utils import crs_representation
from hydromt_fiat.utils import (
    EXPOSURE,
    EXPOSURE_GRID_FILE,
    EXPOSURE_GRID_SETTINGS,
    GRID,
    MODEL_TYPE,
    REGION,
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
    region_filename : str
        The path to use for reading and writing of the region data by default.
        By default "region.geojson".
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: str = f"{EXPOSURE}/spatial.nc",
        region_component: str | None = None,
        region_filename: str = f"{REGION}.geojson",
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
    ) -> None:
        """Read the exposure grid data.

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root. If None, the value is either taken from
            the model configurations or the `_filename` attribute, by default None.
        **kwargs : dict
            Additional keyword arguments to be passed to the `read_nc` method.
        """
        # Sort the filename
        # Hierarchy: 1) signature, 2) config file, 3) default
        filename = (
            filename
            or self.model.config.get(EXPOSURE_GRID_FILE, abs_path=True)
            or self._filename
        )
        # Read the data
        read_path = Path(self.root.path, filename)
        logger.info(f"Reading the exposure grid file at {read_path.as_posix()}")
        # Read with the (old) read function from hydromt-core
        ncs = _read_nc(
            read_path,
            self.root.path,
            single_var_as_array=False,
            mask_and_scale=False,
            **kwargs,
        )
        # Set the datasets
        for ds in ncs.values():
            self.set(ds)

    @hydromt_step
    def write(
        self,
        filename: str | None = None,
        gdal_compliant: bool = True,
        **kwargs,
    ) -> None:
        """Write the exposure grid data.

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root. If None, the value is either taken from
            the model configurations or the `_filename` attribute, by default None.
        gdal_compliant : bool, optional
            If True, write grid data in a way that is compatible with GDAL,
            by default True.
        **kwargs : dict
            Additional keyword arguments to be passed to the `write_nc` method.
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
        self._data = force_ns(self.data)  # Force north south before writing
        _write_nc(
            {GRID: self.data},
            write_path.as_posix(),
            root=self.root.path,
            gdal_compliant=gdal_compliant,
            rename_dims=False,
            force_overwrite=self.root.mode.is_override_mode(),
            force_sn=False,
            **kwargs,
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

    ## Mutating methods
    @hydromt_step
    def clear(self):
        """Clear the exposure grid data."""
        self._data = None
        self._initialize_grid(skip_read=True)

    @hydromt_step
    def clip(
        self,
        geom: gpd.GeoDataFrame,
        buffer: int = 1,
        inplace: bool = False,
    ) -> xr.Dataset | None:
        """Clip the exposure data based on geometry.

        Parameters
        ----------
        geom : gpd.GeoDataFrame
            The area to clip the data to.
        buffer : int, optional
            A buffer of cells around the clipped area to keep, by default 1.
        inplace : bool, optional
            Whether to do the clipping in place or return a new xr.Dataset,
            by default False.

        Returns
        -------
        xr.Dataset | None
            Return a dataset if the inplace is False.
        """
        # Check whether it has the necessary dims
        try:
            self.data.raster.set_spatial_dims()
        except ValueError:
            return None

        # If so, clip the data
        data = self.data.raster.clip_geom(geom, buffer=buffer)
        # If inplace, just set the data and return nothing
        if inplace:
            self._data = data
            return None
        return data

    def set(
        self,
        data: xr.Dataset | xr.DataArray,
        name: str | None = None,
    ) -> None:
        """Set data in the exposure grid component.

        Parameters
        ----------
        data : xr.Dataset | xr.DataArray
            The data to set.
        name : str | None, optional
            The name of the data when data is of type DataArray and the DataArray
            has not name yet, by default None.
        """
        # Make sure the grid exists
        self._initialize_grid()
        assert self._data is not None

        # First check the input and typing
        if isinstance(data, xr.DataArray):
            if data.name is None and name is None:
                raise ValueError("DataArray can't be set without a name")
            data.name = name
            data = data.to_dataset()
        if not isinstance(data, xr.Dataset):
            raise TypeError(f"Wrong input data type: '{data.__class__.__name__}'")

        # Force ns orientation
        data = force_ns(data)
        # Set thet data
        if len(self._data) == 0:  # empty grid
            self._data = data
        else:
            for dvar in data.data_vars:
                if dvar in self._data:
                    logger.warning(f"Replacing grid map: '{dvar}'")
                self._data[dvar] = data[dvar]

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
                exposure_link_fname
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
