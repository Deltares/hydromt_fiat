import osmnx as ox
import logging
from shapely.geometry import Polygon


def get_assets_from_osm(polygon: Polygon):
    tags = {"building": True}  # this is the tag we use to find the correct OSM data
    footprints = ox.features.features_from_polygon(
        polygon, tags
    )  # then we query the data

    if footprints.empty:
        logging.warning("No buildings found from OSM")
        return None

    logging.info(f"Total number of buildings found from OSM: {len(footprints)}")

    # We filter the data on polygons and multipolygons
    footprints = footprints.loc[
        (footprints.geometry.type == "Polygon")
        | (footprints.geometry.type == "MultiPolygon")
    ]
    footprints = footprints.reset_index()
    footprints = footprints.loc[:, ["osmid", "geometry"]]
    return footprints


def get_roads_from_osm(
    polygon: Union[Polygon, Path, str]
) ->gpd.GeoDataFrame:
    tag = {
        "highway": ["motorway"]
    }  # this is the tag we use to find the correct OSM data
    if isinstance(polygon,(Path,str)): 
        gdf = gpd.read_file(polygon)
        polygon =gdf.geometry.iloc[0]
    else:
        return polygon
    
    roads = ox.features.features_from_polygon(
        polygon, tags=tag
    )  # then we query the data

    if roads.empty:
        logging.warning("No road network found from OSM")
        return None

    logging.info(f"Total number of roads found from OSM: {len(roads)}")

    # Not sure if this is needed here and maybe filter for the columns that we need
    roads = roads.loc[
        (roads.geometry.type == "Polygon")
        | (roads.geometry.type == "MultiPolygon")
        | (roads.geometry.type == "LineString")
    ]
    roads = roads.reset_index(drop=True)
    roads.rename(columns={"element_type": "type"}, inplace=True)

    return roads


def get_landuse_from_osm(polygon: Polygon):
    tags = {"landuse": True}  # this is the tag we use to find the correct OSM data
    landuse = ox.features.features_from_polygon(polygon, tags)  # then we query the data

    if landuse.empty:
        logging.warning("No land use data found from OSM")
        return None

    logging.info(f"Total number of land use polygons found from OSM: {len(landuse)}")

    # TODO Check this piece of code, no data found for the currently tested polygon
    # We filter the data on polygons and multipolygons and select the columns we need
    landuse = landuse.loc[
        (landuse.geometry.type == "Polygon") | (landuse.geometry.type == "MultiPolygon")
    ]
    landuse = landuse.reset_index(drop=True)
    landuse.rename(columns={"element_type": "type"}, inplace=True)
    return landuse


if __name__ == "__main__":
    _polygon = Polygon(
        [
            [-80.21997289327112, 25.83897611793664],
            [-80.21997289327112, 25.86427542636784],
            [-80.24609330530801, 25.86427542636784],
            [-80.24609330530801, 25.83897611793664],
            [-80.21997289327112, 25.83897611793664],
        ]
    )
    get_landuse_from_osm(_polygon)

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
