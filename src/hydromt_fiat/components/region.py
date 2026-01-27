"""The region components."""

from logging import Logger, getLogger
from pathlib import Path
from typing import cast

import geopandas as gpd
from hydromt.model import Model
from hydromt.model.components.spatial import SpatialModelComponent
from pyproj.crs import CRS

from hydromt_fiat.utils import REGION

__all__ = ["RegionComponent"]

logger: Logger = getLogger(f"hydromt.{__name__}")


class RegionComponent(SpatialModelComponent):
    """Component for the region.

    Contains a single geometry at most, i.e. the region.

    Parameters
    ----------
    model : Model
        HydroMT model instance (FIATModel).
    filename : str, optional
        The path to use for reading and writing of component data by default.
        by default "region.geojson" i.e. one file.
    """

    _build = True

    def __init__(
        self,
        model: Model,
        *,
        filename: str = f"{REGION}.geojson",
    ):
        self._data: gpd.GeoDataFrame | None = None
        self._filename: str = filename
        self._init: bool = False  # Prevention of recursion
        super().__init__(
            model=model,
        )

    ## Private methods
    def _initialize(self, skip_read=False) -> None:
        """Initialize region."""
        self._init = True
        if self.root.is_reading_mode() and not skip_read:
            self.read()

    ## Properties
    @property
    def _region_data(self) -> gpd.GeoDataFrame | None:
        # Use the total bounds of all geometries as region
        if self.data is None:
            return None
        return self.data

    @property
    def data(self) -> gpd.GeoDataFrame | None:
        """Model geometries.

        Return `geopandas.GeoDataFrame`.
        """
        if self._data is None and not self._init:
            self._initialize()
        return self._data

    ## I/O methods
    def read(self, filename: str | None = None, **kwargs) -> None:
        """Read model region data.

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root.
            If None, the value is taken from the `_filename` attribute,
            by default None.
        **kwargs : dict
            Additional keyword arguments that are passed to the
            `geopandas.read_file` function.
        """
        self.root._assert_read_mode()
        self._initialize(skip_read=True)

        # Sort the pathing
        f = filename or self._filename
        read_path = self.root.path / f
        if not read_path.is_file():
            return

        # Read the data
        logger.info(f"Reading the model region file at {read_path.as_posix()}")
        data = cast(gpd.GeoDataFrame, gpd.read_file(read_path, **kwargs))
        self.set(data=data)

    def write(
        self,
        filename: str | None = None,
        to_wgs84: bool = False,
        **kwargs,
    ) -> None:
        """Write model region data.

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root.
            If None, the value is taken from the `_filename` attribute,
            by default None.
        to_wgs84 : bool, optional
            If True, the geoms will be reprojected to WGS84(EPSG:4326)
            before they are written. By default False.
        **kwargs : dict
            Additional keyword arguments that are passed to the
            `geopandas.to_file` function.
        """
        self.root._assert_write_mode()

        # If nothing to write, return
        if self.data is None:
            logger.info("No region data found, skip writing.")
            return

        # Sort the filename
        # Hierarchy: 1) signature, 2) default
        filename = filename or self._filename
        write_path = Path(self.root.path, filename)

        # Write the file
        data = self.data
        if len(data) == 0:
            logger.warning("Region is empty. Skipping...")
            return

        logger.info(f"Writing the model region file to {write_path.as_posix()}")
        # Create dir if not there
        if not write_path.parent.is_dir():
            write_path.parent.mkdir(parents=True, exist_ok=True)

        # Reproject to WGS84 is wantead
        if to_wgs84 and (
            kwargs.get("driver") == "GeoJSON"
            or str(write_path).lower().endswith(".geojson")
        ):
            data.to_crs(epsg=4326, inplace=True)
        # Write
        data.to_file(write_path, **kwargs)

    ## Mutating methods
    def clear(self):
        """Clear the region."""
        self._data = None
        self._initialize(skip_read=True)

    def reproject(
        self,
        crs: CRS | int | str,
        inplace: bool = False,
    ) -> gpd.GeoDataFrame | None:
        """Reproject the model region.

        Parameters
        ----------
        crs : CRS | int | str
            The coordinate system to reproject to.
        inplace : bool, optional
            Whether to do the reprojection in place or return a new GeoDataFrame.
            By default False.
        """
        # Set the crs
        if not isinstance(crs, CRS):
            crs = CRS.from_user_input(crs)

        # Check for equal crs
        if self.data is None or crs == self.crs:
            return None

        # Reproject
        data = self.data.to_crs(crs)

        # Check return or inplace
        if inplace:
            self._data = data
            return None
        return data

    def set(
        self,
        data: gpd.GeoDataFrame | gpd.GeoSeries,
        replace: bool = False,
    ) -> None:
        """Set a region.

        If a region is already present, the new region will be merged with in one
        already present in a union.

        Parameters
        ----------
        data : gpd.GeoDataFrame | gpd.GeoSeries
            New geometry data to add.
        replace : bool, optional
            Whether or not to replace the current region outright. If set to False,
            a union is created between the existing and given geometries.
            By default False.
        """
        if self.data is not None:
            logger.warning("Replacing/ updating region")

        if isinstance(data, gpd.GeoSeries):
            data = cast(gpd.GeoDataFrame, data.to_frame())

        # Verify if a geom is set to model crs and if not sets geom to model crs
        model_crs = self.crs
        if model_crs and model_crs != data.crs:
            data.to_crs(model_crs, inplace=True)

        # Get rid of columns that aren't geometry
        data = data["geometry"].to_frame()

        # Make a union with the current region geodataframe
        cur = self.data
        if cur is not None and not data.equals(cur) and not replace:
            data = data.union(cur)

        self._data = data
