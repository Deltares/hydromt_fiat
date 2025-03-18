"""Exposure workflows."""

import logging

import geopandas as gpd
import osmnx as ox
from shapely.geometry import Polygon

logger = logging.getLogger(__name__)
__all__ = []


def get_osm_data(polygon: Polygon, tags: dict) -> dict[gpd.GeoDataFrame]:
    data_dict = {}

    tag_attributes = {
        "building": {
            "geom_type": ["Multipolygon", "Polygon"],
        },
        "amenity": {
            "geom_type": ["Multipolygon", "Polygon"],
        },
        "landuse": {
            "geom_type": ["Multipolygon", "Polygon"],
        },
        "highway": {"geom_type": ["LineString", "MultiLinestring"]},
    }

    for tag, value in tags.items():
        footprints = ox.features.features_from_polygon(polygon, {tag: value})

        if footprints.empty:
            logger.warning(f"No {tag} features found for polygon")
            continue

        logger.info(f"Total number of {tag} found from OSM: {len(footprints)}")

        if tag in tag_attributes:
            footprints = footprints.loc[
                footprints.geometry.type in tag_attributes[tag]["geom_type"]
            ]
            footprints = footprints.reset_index(drop=True)
        data_dict[tag] = footprints[["geometry", tag]]
    return data_dict
