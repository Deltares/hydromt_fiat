"""Custom geometry component for HydroMT-FIAT."""

import logging
from abc import abstractmethod

import geopandas as gpd
import numpy as np
import shapely.geometry as sg
from hydromt.model import Model
from hydromt.model.components import SpatialModelComponent
from hydromt.model.steps import hydromt_step
from pyproj.crs import CRS

__all__ = ["GeomsCustomComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class GeomsCustomComponent(SpatialModelComponent):
    """Base class for FIAT geometry based components."""

    def __init__(
        self,
        model: Model,
        *,
        region_component: str | None = None,
    ):
        self._data: dict[str, gpd.GeoDataFrame] | None = None
        super().__init__(
            model=model,
            region_component=region_component,
            region_filename=None,
        )

    ## Private methods
    def _initialize(self, skip_read=False) -> None:
        """Initialize geoms data structure (dict)."""
        if self._data is None:
            self._data = dict()
            if self.root.is_reading_mode() and not skip_read:
                self.read()

    ## Properties
    @property
    def _region_data(self) -> gpd.GeoDataFrame | None:
        # Use the total bounds of all geometries as region
        if len(self.data) == 0:
            return None
        bounds = np.column_stack([geom.total_bounds for geom in self.data.values()])
        total_bounds = (
            bounds[0, :].min(),
            bounds[1, :].min(),
            bounds[2, :].max(),
            bounds[3, :].max(),
        )
        region = gpd.GeoDataFrame(geometry=[sg.box(*total_bounds)], crs=self.model.crs)

        return region

    @property
    def data(self) -> dict[str, gpd.GeoDataFrame | gpd.GeoSeries]:
        """Geometries.

        Return dict of `geopandas.GeoDataFrame` or `geopandas.GeoSeries`.
        """
        if self._data is None:
            self._initialize()
        assert self._data is not None
        return self._data

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
    def clear(self):
        """Clear the geometry data."""
        self._data = None
        self._initialize(skip_read=True)

    @hydromt_step
    def clip(
        self,
        geom: gpd.GeoDataFrame,
        inplace: bool = False,
    ) -> dict[str, gpd.GeoDataFrame] | None:
        """Clip the vector data.

        Geometry needs to be in the same crs (or lack thereof) as the data.

        Parameters
        ----------
        geom : gpd.GeoDataFrame
            The area to clip the data to.
        inplace : bool, optional
            Whether to do the clipping in place or return a new dictionary containing
            the GeoDataFrames, by default False.

        Returns
        -------
        dict[str, gpd.GeoDataFrame] | None
            Return a dataset if the inplace is False.
        """
        data = {}
        if len(self.data) == 0:
            return None
        # Loop through all the existing GeoDataFrames and clip them
        for key, gdf in self.data.items():
            if geom.crs and gdf.crs and gdf.crs != geom.crs:
                geom = geom.to_crs(gdf.crs)
            data[key] = gdf.clip(geom)
        # If inplace is true, just set the new data and return None
        if inplace:
            self._data = data
            return None
        return data

    @hydromt_step
    def reproject(
        self,
        crs: CRS | int | str,
        inplace: bool = False,
    ) -> dict[str, gpd.GeoDataFrame] | None:
        """Reproject the vector data.

        Parameters
        ----------
        crs : CRS | int | str
            The coordinate system to reproject to.
        inplace : bool, optional
            Whether to do the reprojection in place or return a new dictionary
            containing the GeoDataFrame's, by default False.

        Returns
        -------
        dict[str, gpd.GeoDataFrame] | None
            Return a dictionary of GeoDataFrame's is inplace is False.
        """
        # Set the crs
        if not isinstance(crs, CRS):
            crs = CRS.from_user_input(crs)

        data = {}
        # Go through the vector data
        for name, gdf in self.data.items():
            # If no crs, cant reproject
            # If equal, do nothing
            if gdf.crs is None or crs == gdf.crs:
                data[name] = gdf
                continue
            data[name] = gdf.to_crs(crs)

        # If inplace, just set the data and return nothing
        if inplace:
            self._data = data
            return None
        return data

    def set(
        self,
        data: gpd.GeoDataFrame,
        name: str,
    ) -> None:
        """Set data in the geoms component.

        Arguments
        ---------
        data : gpd.GeoDataFrame
            New geometry data to add.
        name : str
            Geometry name.
        """
        self._initialize()
        assert self._data is not None
        if name in self._data and id(self._data.get(name)) != id(data):
            logger.warning(f"Replacing geom: {name}")

        if "fid" in data.columns:
            logger.warning(
                f"'fid' column encountered in {name}, \
column will be removed"
            )
            data.drop("fid", axis=1, inplace=True)

        # Set the data
        self._data[name] = data
