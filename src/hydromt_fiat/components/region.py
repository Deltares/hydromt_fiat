"""Custom region components."""

from logging import Logger, getLogger
from pathlib import Path
from typing import cast

import geopandas as gpd
from hydromt.model import Model
from hydromt.model.components.spatial import SpatialModelComponent
from hydromt.model.steps import hydromt_step

from hydromt_fiat.utils import REGION

__all__ = ["RegionComponent"]

logger: Logger = getLogger(f"hydromt.{__name__}")


class RegionComponent(SpatialModelComponent):
    """Custom component for region.

    Parameters
    ----------
    model : Model
        HydroMT model instance.
    filename : str, optional
        The path to use for reading and writing of component data by default.
        by default "region.geojson" i.e. one file.
    region_component : str, optional
        The name of the region component to use as reference for this component's
        region. If None, the region will be set to the union of all geometries in
        the data dictionary.
    region_filename : str, optional
        The path to use for writing the region data to a file. By default
        "region.geojson".
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: str = "region.geojson",
        region_component: str | None = None,
        region_filename: str = "region.geojson",
    ):
        self._data: dict[str, gpd.GeoDataFrame | gpd.GeoSeries] | None = None
        self._filename: str = filename
        super().__init__(
            model=model,
            region_component=region_component,
            region_filename=region_filename,
        )

    def _initialize(self, skip_read=False) -> None:
        """Initialize region."""
        if self._data is None:
            self._data = dict()
            if self.root.is_reading_mode() and not skip_read:
                self.read()

    ## Properties
    @property
    def data(self) -> dict[str, gpd.GeoDataFrame | gpd.GeoSeries]:
        """Model geometries.

        Return dict of `geopandas.GeoDataFrame` or `geopandas.GeoSeries`.
        """
        if self._data is None:
            self._initialize()

        return self._data

    @property
    def _region_data(self) -> gpd.GeoDataFrame | None:
        # Use the total bounds of all geometries as region
        if len(self.data) == 0:
            return None
        return self.data[REGION]

    ## I/O methods
    @hydromt_step
    def read(self, filename: str | None = None, **kwargs) -> None:
        """Read model region data.

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root.
            If None, the path that was provided at init will be used.
        **kwargs : dict
            Additional keyword arguments that are passed to the
            `geopandas.read_file` function.
        """
        self.root._assert_read_mode()
        self._initialize(skip_read=True)
        f = filename or self._filename
        read_path = self.root.path / f
        if not read_path.is_file():
            return
        logger.info(f"Reading the model region file at {read_path.as_posix()}")
        geom = cast(gpd.GeoDataFrame, gpd.read_file(read_path, **kwargs))
        self.set(geom=geom)

    @hydromt_step
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
            If None, the path that was provided at init will be used.
        to_wgs84 : bool, optional
            If True, the geoms will be reprojected to WGS84(EPSG:4326)
            before they are written.
        **kwargs : dict
            Additional keyword arguments that are passed to the
            `geopandas.to_file` function.
        """
        self.root._assert_write_mode()

        # If nothing to write, return
        if REGION not in self.data:
            logger.info("No region data found, skip writing.")
            return

        # Sort the filename
        # Hierarchy: 1) signature, 2) default
        filename = filename or self._filename
        write_path = Path(self.root.path, filename)

        # Write the file(s)
        logger.info("Writing the model region file..")
        gdf = self.data[REGION]
        if len(gdf) == 0:
            logger.warning("Region is empty. Skipping...")
            return

        # Create dir if not there
        if not write_path.parent.is_dir():
            write_path.parent.mkdir(parents=True, exist_ok=True)

        # Reproject to WGS84 is wantead
        if to_wgs84 and (
            kwargs.get("driver") == "GeoJSON"
            or str(write_path).lower().endswith(".geojson")
        ):
            gdf.to_crs(epsg=4326, inplace=True)
        # Write
        gdf.to_file(write_path, **kwargs)

    ## Set(up) methods
    def set(self, geom: gpd.GeoDataFrame | gpd.GeoSeries) -> None:
        """Add data to the region component.

        If a region is already present, the new region will be merged with in one
        already present in a union.

        Parameters
        ----------
        geom : gpd.GeoDataFrame | gpd.GeoSeries
            New geometry data to add.
        """
        self._initialize()
        if len(self.data) != 0:
            logger.warning("Replacing/ updating region")

        if isinstance(geom, gpd.GeoSeries):
            geom = cast(gpd.GeoDataFrame, geom.to_frame())

        # Verify if a geom is set to model crs and if not sets geom to model crs
        model_crs = self.model.crs
        if model_crs and model_crs != geom.crs:
            geom.to_crs(model_crs.to_epsg(), inplace=True)

        # Get rid of columns that aren't geometry
        geom = geom["geometry"].to_frame()

        # Make a union with the current region geodataframe
        cur = self._data.get(REGION)
        if cur is not None and not geom.equals(cur):
            geom = geom.union(cur)

        self._data[REGION] = geom
