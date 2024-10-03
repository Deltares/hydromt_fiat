import pandas as pd
import geopandas as gpd


def detect_delimiter(csvFile):
    """From stackoverflow
    https://stackoverflow.com/questions/16312104/can-i-import-a-csv-file-and-automatically-infer-the-delimiter
    """
    with open(csvFile, "r") as myCsvfile:
        header = myCsvfile.readline()
        if header.find(";") != -1:
            return ";"
        if header.find(",") != -1:
            return ","
    # default delimiter
    return ","


def get_us_county_numbers(
    county_names: list, states_counties_table: pd.DataFrame
) -> list:
    county_numbers = list(
        states_counties_table.loc[
            states_counties_table["COUNTYNAME"].isin(county_names), "COUNTYFP"
        ].values
    )
    county_numbers = [str(cn).zfill(3) for cn in county_numbers]
    return county_numbers


def rename_geoid_short(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Create string from GEO_ID short
    for index, row in gdf.iterrows():
        BG_string = f"BG: {row['GEOID_short']}"
        gdf.at[index, "GEOID_short"] = BG_string
    return gdf
