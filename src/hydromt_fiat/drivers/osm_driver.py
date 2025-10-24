"""Driver to read OSM data with the OSMnx API."""

import logging
from pathlib import Path
from typing import Any, ClassVar, Set

import geopandas as gpd
import osmnx as ox
from hydromt._typing import StrPath
from hydromt.data_catalog.drivers import GeoDataFrameDriver
from osmnx._errors import InsufficientResponseError
from pyproj.crs import CRS
from shapely.geometry import Polygon

CACHE_DIR = Path.home() / ".cache" / "hydromt_fiat" / "osmnx"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
ox.settings.cache_folder = CACHE_DIR

logger = logging.getLogger(f"hydromt.{__name__}")


class OSMDriver(GeoDataFrameDriver):
    """Driver to read OSM data with the OSMnx API."""

    name = "osm"
    supports_writing = True
    _supported_extensions: ClassVar[Set[str]] = {".gpkg", ".shp", ".geojson", ".fgb"}

    def read(
        self,
        uris: list[str],
        mask: gpd.GeoDataFrame | gpd.GeoSeries,
        *,
        tags: list[str] | None = None,
        geom_type: list[str] | None = None,
        **kwargs,
    ) -> gpd.GeoDataFrame:
        """Read OSM data with the OSMnx API.

        Parameters
        ----------
        uris : list[str]
            List containing single OSM asset type.
        mask : gpd.GeoDataFrame | gpd.GeoSeries
            GeoDataFrame containing the region of interest.
        tags : list[str], optional
            Additional tags to filter the OSM data by, by default None.
        geom_type : list[str], optional
            List of geometry types to filter data with,
            i.e. ['MultiPolygon', 'Polygon'], by default None.

        Returns
        -------
        gpd.GeoDataFrame
            The resulting data.
        """
        if len(uris) > 1:
            raise ValueError("Cannot use multiple uris for reading OSM data.")

        if mask is None:
            raise ValueError("Mask is required to retrieve OSM data")

        if not isinstance(mask, (gpd.GeoDataFrame, gpd.GeoSeries)):
            raise TypeError(
                f"Wrong type: {type(mask)} -> should be GeoDataFrame or GeoSeries"
            )
        uri = uris[0]
        if len(mask) > 1:
            logger.warning(
                "Received multiple geometries for mask, geometries will "
                "be dissolved into single geometry."
            )
            mask = mask.dissolve()

        # Quick check on the crs. If not in WGS84, reproject
        crs = CRS.from_epsg(4326)
        if not mask.crs.equals(crs):
            mask = mask.to_crs(crs)  # WGS84
        polygon = mask.geometry[0]

        # If tags and geom_types are none check if these are supplied as driver options
        if self.options.get("geom_type") and not geom_type:
            geom_type = self.options.get("geom_type")
        if self.options.get("tags") and not tags:
            tags = self.options.get("tags")

        if tags:
            tag: dict[str, Any] = {uri: tags}
        else:
            tag = {uri: True}
        logger.info("Retrieving %s data from OSM API", uri)
        return self.get_osm_data(polygon=polygon, tag=tag, geom_type=geom_type)

    def write(self, path: StrPath, gdf: gpd.GeoDataFrame, **kwargs) -> StrPath:
        """Write OSMNx data to file.

        Parameters
        ----------
        path : StrPath
            Path to write osm data to.
        gdf : gpd.GeoDataFrame
            GeoDataFrame containing OSM data.

        Returns
        -------
        StrPath
            Path to the file.
        """
        path = Path(path)
        ext = path.suffix
        if ext not in self._supported_extensions:
            logger.warning(
                f"driver {self.name} has no support for extension {ext}"
                "switching to .fgb."
            )
            path = path.parent / (path.stem + ".fgb")
        gdf.to_file(path, **kwargs)
        return path

    @staticmethod
    def get_osm_data(
        polygon: Polygon, tag: dict[str, Any], geom_type: list[str] | None
    ) -> gpd.GeoDataFrame:
        """Retrieve OSM data with the OSMnx api.

        Parameters
        ----------
        polygon : Polygon
            Area of interest.
        tag : dict
            OSM tag to filter data with, i.e. {'building': True}.
        geom_type : list[str] | None
            List of geometry types to filter data with,
            i.e. ['MultiPolygon', 'Polygon'].

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with OSM data.

        """
        if not isinstance(polygon, Polygon):
            raise TypeError("Given polygon is not of shapely.geometry.Polygon type")

        try:
            footprints = ox.features.features_from_polygon(polygon, tag)
        except InsufficientResponseError as err:
            logger.error(f"No OSM data retrieved with the following tags: {tag}")
            raise err

        tag_key = list(tag.keys())[0]

        if footprints.empty:
            logger.warning(f"No {tag_key} features found for polygon")
            return None

        logger.info(f"Total number of {tag_key} found from OSM: {len(footprints)}")

        if geom_type:
            footprints = footprints.loc[footprints.geometry.type.isin(geom_type)]

        # Remove multi index
        footprints = footprints.reset_index(drop=True)
        return footprints[["geometry", tag_key]]
