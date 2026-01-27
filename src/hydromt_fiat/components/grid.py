"""Custom grid component for HydroMT-FIAT."""

import logging
from abc import abstractmethod

import geopandas as gpd
import shapely.geometry as sg
import xarray as xr
from hydromt.model import Model
from hydromt.model.components import SpatialModelComponent
from hydromt.model.steps import hydromt_step
from pyproj.crs import CRS

from hydromt_fiat.gis.raster_utils import force_ns

__all__ = ["GridComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class GridComponent(SpatialModelComponent):
    """Base class for FIAT grid based components."""

    _build = True

    def __init__(
        self,
        model: Model,
        *,
        region_component: str | None = None,
    ):
        self._data: xr.Dataset | None = None
        super().__init__(
            model=model,
            region_component=region_component,
            region_filename=None,
        )

    ## Private methods
    def _initialize(self, skip_read: bool = False) -> None:
        """Initialize the internal dataset."""
        if self._data is None:
            self._data = xr.Dataset()
            if self.root.is_reading_mode() and not skip_read:
                self.read()

    ## Properties
    @property
    def _region_data(self) -> gpd.GeoDataFrame | None:
        """Returns the geometry of the model area of interest."""
        if len(self.data) > 0:
            return gpd.GeoDataFrame(geometry=[sg.box(*self.bounds)], crs=self.crs)
        logger.warning("Region could not be derived from the data.")
        return None

    @property
    def bounds(self) -> tuple[float] | None:
        """Return the bounding box of the data."""
        if len(self.data) > 0:
            return self.data.raster.bounds
        logger.warning("Bounding box could not be derived from the data.")
        return None

    @property
    def crs(self) -> CRS | None:
        """Return the data CRS."""
        if self.data.raster is None or self.data.raster.crs is None:
            logger.warning("CRS of data could not be determined.")
            return None
        return CRS(self.data.raster.crs)

    @property
    def data(self) -> xr.Dataset:
        """Return the data.

        Return
        ------
        xr.Dataset
        """
        if self._data is None:
            self._initialize()
        assert self._data is not None
        return self._data

    @property
    def res(self) -> tuple[float] | None:
        """Returns the resolution of the model grid."""
        if len(self.data) > 0:
            return self.data.raster.res
        logger.warning("Resolution could not be derived from the data.")
        return None

    @property
    def transform(self) -> tuple[float] | None:
        """Returns spatial transform of the model grid."""
        if len(self.data) > 0:
            return self.data.raster.transform
        logger.warning("Transform could not be derived from the data.")
        return None

    ## I/O methods
    @abstractmethod
    def read(self):
        """Read method."""
        ...

    @abstractmethod
    def write(self):
        """Write method."""
        ...

    ## Mutating methods
    @hydromt_step
    def clear(self) -> None:
        """Clear the gridded data."""
        self._data = None
        self._initialize(skip_read=True)

    @hydromt_step
    def clip(
        self,
        geom: gpd.GeoDataFrame,
        buffer: int = 1,
        inplace: bool = False,
    ) -> xr.Dataset | None:
        """Clip the gridded data.

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

    @hydromt_step
    def reproject(
        self,
        crs: CRS | int | str,
        inplace: bool = False,
    ) -> xr.Dataset | None:
        """Reproject the gridded data.

        Parameters
        ----------
        crs : CRS | int | str
            The coordinate system to reproject to.
        inplace : bool, optional
            Whether to do the reprojection in place or return a new xr.Dataset,
            by default False.

        Returns
        -------
        xr.Dataset | None
            Return a dataset if the inplace is False.
        """
        # Check for the crs's
        if self.crs is None:
            return None
        if not isinstance(crs, CRS):
            crs = CRS.from_user_input(crs)

        # No need for reprojecting if this is the case
        if crs == self.crs:
            return None

        # Reproject the data
        data = self.data.raster.reproject(dst_crs=crs)
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
        """Set gridded data in the component.

        Parameters
        ----------
        data : xr.Dataset | xr.DataArray
            The data to set.
        name : str | None, optional
            The name of the data when data is of type DataArray and the DataArray
            has not name yet, by default None.
        """
        # Make sure the grid exists
        self._initialize()
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
