"""Custom grid component for HydroMT-FIAT."""

import logging
from abc import abstractmethod
from typing import Any

import geopandas as gpd
import numpy as np
import shapely.geometry as sg
import xarray as xr
from hydromt.model import Model
from hydromt.model.components import SpatialModelComponent
from hydromt.model.steps import hydromt_step
from pyproj.crs import CRS

from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.gis.raster import expand_raster_to_bounds
from hydromt_fiat.gis.raster_utils import check_spatial, force_ns

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
    def _assert_entry(self, name: str, spatial: bool = False):
        keys = [
            item
            for item in self.data.data_vars
            if check_spatial(self.data[item]) == spatial
        ]
        if name not in keys:
            raise RuntimeError(f"Choose from already present data variables: {keys}")

    def _get_attributes(self, attr: str, spatial: bool = False) -> list[Any]:
        """Return attribute from spatial variables."""
        attrs = []
        for var in self.data.data_vars:
            if spatial and not check_spatial(self.data[var]):
                continue
            attrs.append(self.data[var].attrs.get(attr, None))
        return attrs

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
            assert self.bounds is not None
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
    def like(self) -> xr.Dataset | None:
        """Return the spatial representation of the data."""
        if check_spatial(self.data):
            return self.data
        return None

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
        # Check the spatial component
        if not check_spatial(self.data):
            return None

        logger.info(f"Clipping data of {self.__class__.__name__}")
        # If so, clip the data
        data = self.data.raster.clip_geom(geom, buffer=buffer)
        # If inplace, just set the data and return nothing
        if inplace:
            self._data = data
            return None
        return data

    @hydromt_step
    def create_grid(
        self,
        res: float | int | None = None,
        ds_like: xr.DataArray | xr.Dataset | None = None,
        crs: CRS | int | str | None = None,
    ) -> None:
        """Create grid coordinates based on model region or another raster.

        Parameters
        ----------
        res : float | int, optional
            The resolution of the grid made from scratch. The grid will created based
            on this resolution and the extent of the model region. By default None.
        ds_like : xr.DataArray | xr.Dataset, optional
            Create coordinates based on another spatial dataset. This argument is
            ignored if `res` is provided, by default None.
        crs : CRS | int | str, optional
            The coordinate system the data is in, by default None.
        """
        # Quick check on whether we can set it up
        if check_spatial(self.data):
            raise RuntimeError(
                f"{self.__class__.__name__} already contains spatial coordinates",
            )
        # Check on the input
        if res is None and ds_like is None:
            raise ValueError("Provide either `res` or `ds_like`")
        # Quick check on the region
        if self.model.region is None and res is not None:
            raise MissingRegionError(
                "Region is required for creating grid dimensions with \
only resolution set"
            )

        # Get the origin
        if res is not None:
            xo, yno, xno, yo = self.model.region.total_bounds
            # Create the coordinates
            ycoords = np.arange(yo - 0.5 * res, yno - 0.5 * res, -res)
            xcoords = np.arange(xo + 0.5 * res, xno + 0.5 * res, res)
        elif ds_like is not None:
            # Get the coordinates
            ycoords = ds_like[ds_like.raster.y_dim].values
            xcoords = ds_like[ds_like.raster.x_dim].values

        # Assign the coordinates
        self._data = self.data.assign_coords(coords={"y": ycoords, "x": xcoords})
        self.data.raster.set_crs(crs)

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
        # Check the spatial component
        if not check_spatial(self.data):
            return None

        # Check for the crs's
        if self.crs is None:
            return None
        if not isinstance(crs, CRS):
            crs = CRS.from_user_input(crs)

        # No need for reprojecting if this is the case
        if crs == self.crs:
            return None

        logger.info(f"Reproject data in {self.__class__.__name__}")
        # Reproject the data
        data = []
        attrs = self.data.attrs
        for var in self.data.data_vars:
            if not check_spatial(self.data[var]):
                data.append(self.data[var])
                continue
            data.append(self.data[var].raster.reproject(dst_crs=crs))
        # Merge the data back together
        data = xr.merge(data)
        data.attrs = attrs
        # If inplace, just set the data and return nothing
        if inplace:
            self._data = data
            return None
        return data

    def set(
        self,
        data: xr.Dataset | xr.DataArray,
        name: str | None = None,
        expand: bool = False,
    ) -> None:
        """Set gridded data in the component.

        Parameters
        ----------
        data : xr.Dataset | xr.DataArray
            The data to set.
        name : str | None, optional
            The name of the data when data is of type DataArray and the DataArray
            has not name yet, by default None.
        expand : bool, optional
            Whether to expand the data to the bounding box of the model region.
            Nothing is done when the data already covers the region. By default False.
        """
        # Make sure the grid exists
        self._initialize()
        assert self._data is not None

        # First check the input and typing
        if isinstance(data, xr.DataArray):
            if data.name is None and name is None:
                raise ValueError("DataArray can't be set without a name")
            data.name = name or data.name
            data = data.to_dataset()
        if not isinstance(data, xr.Dataset):
            raise TypeError(f"Wrong input data type: '{data.__class__.__name__}'")

        # Expand if necessary
        if (
            check_spatial(data)
            and self.model.region is not None
            and data.raster.crs is not None
            and expand
        ):
            data = expand_raster_to_bounds(
                ds=data,
                bbox=self.model.region.to_crs(data.raster.crs).total_bounds,
            )
        # Force ns orientation
        data = force_ns(data)
        # Set thet data
        for dvar in data.data_vars:
            logger.info(f"Adding {dvar} to {self.__class__.__name__}")
            if dvar in self._data:
                logger.warning(f"Replacing grid map: '{dvar}'")
            self._data[dvar] = data[dvar]
        self._data.attrs.update(data.attrs)
