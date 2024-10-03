import osmnx as ox
import logging
from shapely.geometry import Polygon
import geopandas as gpd
from typing import Union, List

logger = logging.getLogger(__name__)


def get_assets_from_osm(polygon: Polygon) -> gpd.GeoDataFrame:
    tags = {"building": True}  # this is the tag we use to find the correct OSM data

    footprints = ox.features.features_from_polygon(
        polygon, tags
    )  # then we query the data

    if footprints.empty:
        return None

    logger.info(f"Total number of buildings found from OSM: {len(footprints)}")

    # We filter the data on polygons and multipolygons
    footprints = footprints.loc[
        (footprints.geometry.type == "Polygon")
        | (footprints.geometry.type == "MultiPolygon")
    ]
    footprints = footprints.reset_index()
    footprints = footprints.loc[:, ["osmid", "geometry"]]
    return footprints


def get_roads_from_osm(
    polygon: Polygon,
    road_types: Union[str, List[str], bool] = True,
) -> gpd.GeoDataFrame:
    if isinstance(road_types, str):
        road_types = [road_types]

    tag = {"highway": road_types}  # this is the tag we use to find the correct OSM data

    # Make sure that polygon is valid
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    try:
        roads = ox.features.features_from_polygon(
            polygon, tags=tag
        )  # then we query the data
    except (ValueError, TypeError):
        logging.warning(
            "Could not download road data from OSM for the given region and road types."
        )
        return None

    if roads.empty:
        return None

    logger.info(f"Total number of roads found from OSM: {len(roads)}")

    # Not sure if this is needed here and maybe filter for the columns that we need
    roads = roads.loc[
        (roads.geometry.type == "LineString")
        | (roads.geometry.type == "MultiLineString")
    ]
    roads = roads.reset_index(drop=True)

    try:
        roads = roads.loc[:, ["highway", "name", "lanes", "geometry"]]
    except KeyError:
        roads = roads.loc[:, ["highway", "name", "geometry"]]
        logger.info("No attribute 'lanes' found in the OSM roads.")

    return roads


def get_landuse_from_osm(polygon: Polygon) -> gpd.GeoDataFrame:
    tags = {"landuse": True}  # this is the tag we use to find the correct OSM data
    landuse = ox.features.features_from_polygon(polygon, tags)  # then we query the data

    if landuse.empty:
        logger.warning("No land use data found from OSM")
        return None

    logger.info(f"Total number of land use polygons found from OSM: {len(landuse)}")

    # TODO Check this piece of code, no data found for the currently tested polygon
    # We filter the data on polygons and multipolygons and select the columns we need
    landuse = landuse.loc[
        (landuse.geometry.type == "Polygon") | (landuse.geometry.type == "MultiPolygon")
    ]
    landuse = landuse.reset_index(drop=True)
    landuse = landuse[["geometry", "landuse"]]
    return landuse


# # Do a spatial join to connect the buildings with the classes
# # (here we use a buffer area of 100 m around the classes in case there buildings falling completely out of the classes)
# # a more comprehensive spatial join to account for overlapping area can be used as well
# footprints = footprints.explode(ignore_index=True) # tranform multipolygons to single polygons
# footprints_join = gpd.sjoin_nearest(footprints, land_use, how='left', max_distance=100).drop(columns=['index_right'])
# footprints_join =footprints_join[~footprints_join.index.duplicated(keep='first')]  # make sure there are no dublicates from the spatial join
# print('{:.1f} % of the buildings were not classified'.format(sum(footprints_join["Class"].isnull())/len(footprints_join)*100))
# footprints_join


# # Plot a sample of the joined data to check results
# footprints_join.clip(polygon).explore(
#     column="Class", # make choropleth based on "Class" column
#     tooltip="Class", # show "Class" value in tooltip (on hover)
#     popup=True, # show all values in popup (on click)
#     # tiles="CartoDB positron", # use "CartoDB positron" tiles
#     style_kwds=dict(color="black") # use black outline
# )
def get_buildings_from_osm(polygon: Polygon) -> gpd.GeoDataFrame:
    buildings = {
        "building": True
    }  # this is the tag we use to find the correct OSM data
    buildings = ox.features.features_from_polygon(
        polygon, buildings
    )  # then we query the data

    if buildings.empty:
        logging.warning("No buildings data found from OSM")
        return None

    logging.info(f"Total number of buildings found from OSM: {len(buildings)}")

    # TODO Check this piece of code, no data found for the currently tested polygon
    # We filter the data on polygons and multipolygons and select the columns we need
    buildings = buildings.loc[
        (buildings.geometry.type == "Polygon")
        | (buildings.geometry.type == "MultiPolygon")
    ]
    buildings = buildings.loc[buildings["building"].notna()]
    buildings = buildings.reset_index(drop=True)
    buildings = buildings[["geometry", "building"]]
    return buildings  # "building" column with information  https://taginfo.openstreetmap.org/keys/building#values


def get_amenity_from_osm(polygon: Polygon) -> gpd.GeoDataFrame:
    amenity = {"amenity": True}  # this is the tag we use to find the correct OSM data
    amenity = ox.features.features_from_polygon(
        polygon, amenity
    )  # then we query the data

    if amenity.empty:
        logging.warning("No amenity data found from OSM")
        return None

    logging.info(f"Total number of amenity found from OSM: {len(amenity)}")

    # TODO Check this piece of code, no data found for the currently tested polygon
    # We filter the data on polygons and multipolygons and select the columns we need
    amenity = amenity.loc[
        (amenity.geometry.type == "Polygon") | (amenity.geometry.type == "MultiPolygon")
    ]
    amenity = amenity.loc[amenity["amenity"].notna()]
    amenity = amenity.reset_index(drop=True)
    amenity = amenity[["geometry", "amenity"]]
    return amenity  # "amenity" column with information  https://taginfo.openstreetmap.org/keys/building#values
