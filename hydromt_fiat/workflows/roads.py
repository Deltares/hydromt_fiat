import pandas as pd
import geopandas as gpd
from hydromt.gis_utils import utm_crs
import numpy as np


def get_max_potential_damage_roads(
    roads: gpd.GeoDataFrame, road_damage: pd.DataFrame
) -> gpd.GeoDataFrame:
    if roads.crs.is_geographic:
        # If the CRS is geographic, reproject to the nearest UTM zone
        nearest_utm = utm_crs(roads.total_bounds)
        roads = roads.to_crs(nearest_utm)

    unit = roads.crs.axis_info[0].unit_name

    roads = gpd.GeoDataFrame(
        {
            "lanes": pd.to_numeric(roads["lanes"], errors="coerce"),
            "segment_length": roads.length,
            "geometry": roads["geometry"],
        }
    )
    # Create dictionary of damages per number of lanes
    damage_dic = dict(zip(road_damage["lanes"], road_damage["cost [USD/ft]"]))

    # Step 3: Iterate through the DataFrame column and retrieve corresponding values
    roads["lanes"] = [
        1 if (np.isnan(lane)) or (lane == 0) else lane for lane in list(roads["lanes"])
    ]
    roads["damage_value"] = roads["lanes"].map(damage_dic)

    # Potentially convert the length to meters
    roads["max_damage_structure"] = roads["damage_value"] * roads["segment_length"]
    if unit == "meters" or unit == "metre" or unit == "m":
        roads["max_damage_structure"] = roads["max_damage_structure"] * 0.3048
    else:
        print(
            "You are using the wrong unit for the segment length. Please use <'foot/feet/ft'> or <'meters/metre/m'>"
        )

    return roads[["max_damage_structure", "segment_length"]]


def get_road_lengths(roads):
    if roads.crs.is_geographic:
        # If the CRS is geographic, reproject to the nearest UTM zone
        nearest_utm = utm_crs(roads.total_bounds)
        roads = roads.to_crs(nearest_utm)
    return roads.length
