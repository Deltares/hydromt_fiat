import pandas as pd
import geopandas as gpd
from hydromt.gis_utils import utm_crs
import numpy as np


def add_max_potential_damage_roads(
    roads: gpd.GeoDataFrame, road_damage: pd.DataFrame
) -> gpd.GeoDataFrame:
    if roads.crs.is_geographic:
        # If the CRS is geographic, reproject to the nearest UTM zone
        nearest_utm = utm_crs(roads.total_bounds)
        roads_utm = roads.to_crs(nearest_utm)

    roads = gpd.GeoDataFrame(
        {
            "highway": roads["highway"],
            "lanes": pd.to_numeric(roads["lanes"], errors="coerce"),
            "segment_length": roads_utm.length,
            "geometry": roads["geometry"],
        }
    )
    # Create dictionary of damages per number of lanes
    damage_dic = dict(zip(road_damage["lanes"], road_damage["cost [USD/ft]"]))

    damage_per_foot_row = []
    # Step 3: Iterate through the DataFrame column and retrieve corresponding values
    for index, row in roads.iterrows():
        # print(row['lanes'])
        if np.isnan(row["lanes"]) or row["lanes"] == 0:
            row["lanes"] = 1
        else:
            row["lanes"] = row["lanes"]
        if row["lanes"] in damage_dic:
            damage_per_foot = damage_dic[row["lanes"]]
            damage_per_foot_row.append(damage_per_foot)
        else:
            print("No lane found")

    # Potentially convert the length to meters
    if unit == "foot" or unit == "feet" or unit == "ft":
        roads["maximum_potential_damage"] = (
            damage_per_foot * roads["segment_length"]
        )
    elif unit == "meter" or unit == "metre" or unit == "m":
        roads["maximum_potential_damage"] = (
            damage_per_foot * roads["segment_length"] * 0.3048
        )
    else:
        print(
            "You are using wrong unit for the segment length. Please use <'foot'> or <'meter/metre/m'>"
        )

    return roads
