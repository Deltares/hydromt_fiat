"""Custom grid component for HydroMT-FIAT."""

import logging
from abc import abstractmethod

import geopandas as gpd
import xarray as xr
from hydromt.model.components import GridComponent

from hydromt_fiat.gis.raster_utils import force_ns

__all__ = ["CustomGridComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class CustomGridComponent(GridComponent):
    """Base class for FIAT grid based components."""

    ## Mutating methods
    def clear(self) -> None:
        """Clear the gridded data."""
        self._data = None
        self._initialize_grid(skip_read=True)

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
    @abstractmethod
    def setup(self, *args, **kwargs) -> None:
        """Set up method."""
        ...
