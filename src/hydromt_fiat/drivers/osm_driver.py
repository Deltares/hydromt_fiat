"""Driver to read OSM data with the OSMnx API."""

import logging
from pathlib import Path
from typing import ClassVar, Set

import geopandas as gpd
import osmnx as ox
from hydromt._typing import StrPath
from hydromt.data_catalog.drivers import GeoDataFrameDriver
from osmnx._errors import InsufficientResponseError
from shapely.geometry import Polygon

cache_path = Path.home() / ".cache" / "osmnx"
cache_path.mkdir(exist_ok=True)
ox.settings.cache_folder = cache_path

logger = logging.getLogger(__name__)


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
        """Read OSM data with the OSMnx API."""
        if len(uris) > 1:
            raise ValueError("Cannot use multiple uris for reading OSM data.")

        if not isinstance(mask, (gpd.GeoDataFrame, gpd.GeoSeries)):
            raise ValueError("Missing mask argument for reading OSM geometries")
        uri = uris[0]
        polygon = mask.geometry[0]

        # If tags and geom_types are none check if these are supplied as driver options
        if self.options.get("geom_type") and not geom_type:
            geom_type = self.options.get("geom_type")
        if self.options.get("tags") and not tags:
            tags = self.options.get("tags")

        if tags:
            tag = {uri: tags}
        else:
            tag = {uri: True}
        logger.info("Retrieving %s data from OSM API", uri)
        return self._get_osm_data(polygon=polygon, tag=tag, geom_type=geom_type)

    def write(self, path: StrPath, gdf: gpd.GeoDataFrame, **kwargs):
        """Write OSMNx data to file."""
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
    def _get_osm_data(
        polygon: Polygon, tag: dict, geom_type: list[str] | None
    ) -> gpd.GeoDataFrame:
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
