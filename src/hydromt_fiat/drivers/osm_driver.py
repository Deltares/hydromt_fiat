"""Driver to read OSM data with the OSMnx API."""

import logging
from pathlib import Path
from typing import Any, ClassVar, Set

import geopandas as gpd
import osmnx as ox
from hydromt.data_catalog.drivers import GeoDataFrameDriver
from hydromt.typing import StrPath
from osmnx._errors import InsufficientResponseError
from pyproj.crs import CRS
from shapely.geometry import MultiPolygon, Polygon

CACHE_DIR = Path.home() / ".cache" / "hydromt_fiat" / "osmnx"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
ox.settings.cache_folder = CACHE_DIR

logger = logging.getLogger(f"hydromt.{__name__}")


def osm_request(
    polygon: MultiPolygon | Polygon,
    tags: dict[str, Any],
    geom_type: list[str] | None = None,
    reduce: bool = True,
) -> gpd.GeoDataFrame:
    """Retrieve OSM data with the OSMnx api.

    Parameters
    ----------
    polygon : MultiPolygon | Polygon
        Area of interest.
    tags : dict
        OSM tag to filter data with, i.e. {'building': True}.
    geom_type : list[str], optional
        List of geometry types to filter data with,
        i.e. ['MultiPolygon', 'Polygon'].
    reduce : bool, optional
        Whether or not to reduce the output geodataframe to the columns corresponding
        to the tags and (of course) the geometry column. By default True.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame with OSM data.

    """
    if not isinstance(polygon, (Polygon, MultiPolygon)):
        raise TypeError("Given geometry is not a (multi)polygon")

    try:
        items = ox.features.features_from_polygon(polygon, tags)
    except InsufficientResponseError as err:
        logger.error(f"No OSM data retrieved with the following tags: {tags}")
        raise err

    tag_keys = list(tags.keys())

    if items.empty:
        logger.warning(f"No {tag_keys} features found for polygon")
        return None

    logger.info(f"Number of {tag_keys} items found from OSM: {len(items)}")

    if geom_type is not None:
        items = items.loc[items.geometry.type.isin(geom_type)]

    # Remove multi index
    items = items.reset_index(drop=True)
    if reduce:
        return items[[*tag_keys, "geometry"]]
    return items


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
        tags: dict[str, Any] | None = None,
        geom_type: list[str] | None = None,
        **kwargs,
    ) -> gpd.GeoDataFrame:
        """Read OSM data with the OSMnx api.

        Parameters
        ----------
        uris : list[str]
            List containing single OSM asset type.
        mask : gpd.GeoDataFrame | gpd.GeoSeries
            GeoDataFrame containing the region of interest.
        tags : dict[str, Any], optional
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
        options = self.options.to_dict()
        geom_type = geom_type or options.get("geom_type")
        tags = {uri: tags or options.get("tags") or True}

        # Get and return the data
        logger.info("Retrieving %s data from OSM API", uri)
        return osm_request(
            polygon=polygon,
            tags=tags,
            geom_type=geom_type,
        )

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
