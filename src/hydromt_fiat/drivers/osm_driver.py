"""Driver to read OSM data with the OSMnx API."""

import logging
from pathlib import Path
from typing import ClassVar, Set

import geopandas as gpd
import osmnx as ox
from hydromt._typing import StrPath
from hydromt.data_catalog.drivers import GeoDataFrameDriver
from shapely.geometry import Polygon

logger = logging.getLogger(__name__)


class OSMDriver(GeoDataFrameDriver):
    """Driver to read OSM data with the OSMnx API."""

    name = "osm"
    supports_writing = True
    _supported_extensions: ClassVar[Set[str]] = {".gpkg", ".shp", ".geojson", ".fgb"}

    def read(
        self,
        uris: list[str],
        region: gpd.GeoDataFrame,
        *,
        tags: list[str],
        geom_type: list[str] | None = None,
    ) -> gpd.GeoDataFrame:
        """Read OSM data with the OSMnx API."""
        if len(uris) > 1:
            raise ValueError("Cannot use multiple uris for reading OSM data.")

        if not region:
            raise ValueError("Missing region argument for reading OSM geometries")
        uri = uris[0]
        polygon = region.geometry
        if tags:
            tag = dict(uri=tags)
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
            path = path.parent / path.stem / ".fgb"
        gdf.to_file(path, **kwargs)

    @staticmethod
    def _get_osm_data(
        polygon: Polygon, tag: dict, geom_type: list[str] | None
    ) -> gpd.GeoDataFrame:
        if not isinstance(polygon, Polygon):
            raise ValueError("Given polygon is not of shapely.geometry.Polygon type")

        footprints = ox.features.features_from_polygon(polygon, tag)

        tag_key = list(tag.keys())[0]

        if footprints.empty:
            logger.warning(f"No {tag_key} features found for polygon")
            return None

        logger.info(f"Total number of {tag_key} found from OSM: {len(footprints)}")

        if geom_type:
            footprints = footprints.loc[footprints.geometry.type.isin(geom_type)]
            footprints = footprints.reset_index(drop=True)
        return footprints[["geometry", tag_key]]
