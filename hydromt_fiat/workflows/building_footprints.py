import geopandas as gpd
from typing import List, Union
from pathlib import Path
import math 
import hydromt
from hydromt import gis_utils
import pandas as pd


def process_value(value):
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    elif isinstance(value, list) and len(value) > 1:
        return ", ".join(value)
    else:
        return value

def join_exposure_building_footprint(
    exposure_gdf: gpd.GeoDataFrame,
    building_footprint_fn: Union[str, Path],
    attribute_name: str,
    column_name: str = "BF_FID",
) -> gpd.GeoDataFrame:
    """_summary_

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        Exposure data to join the building footprints to as "BF_FID".
    building_footprint_fn : Union[str, Path]
        Path(s) to the building footprint.
    attribute_name : str
        Name of the building footprint ID to join.
    column_name : str = "BF_FID"
        Name of building footprint in new exposure output


    Returns
    -------
    gpd.GeoDataFrame
        _An update exposure GeoDataFrame including the building footprints_
    """
    
    bf_gdf = gpd.read_file(building_footprint_fn)

    #Add index column with default name
    bf_gdf['B_footprint'] = range(1,len(bf_gdf)+1,1)

    # check the projection of both gdf and if not match, reproject
    if exposure_gdf.crs != bf_gdf.crs:
        bf_gdf = bf_gdf.to_crs(exposure_gdf.crs)

      
    assert attribute_name in bf_gdf.columns, f"Attribute {attribute_name} not found in {building_footprint_fn}"
    
    #Check for unique BF-FID
    assert bf_gdf[attribute_name].is_unique, f"Building footprint ID returns duplicates. Building footprint ID should be unique."

    # If you overwrite the exposure_gdf with the joined data, you can append all 
    # aggregation areas to the same exposure_gdf
    exposure_gdf = gpd.sjoin(
        exposure_gdf,
        bf_gdf[["geometry", attribute_name]],
        op="intersects",
        how="left",
    )
    # aggregate the data if duplicates exist
    for i in range(len(exposure_gdf["B_footprint"])):
        if math.isnan(exposure_gdf["B_footprint"].iloc[i]):
            continue
        elif isinstance(exposure_gdf["B_footprint"].iloc[i], float):
                # Convert to integer to remove decimal part
            integer_value = int(exposure_gdf["B_footprint"].iloc[i])
            exposure_gdf["B_footprint"].iloc[i] = str(integer_value)
            

    aggregated = (
        exposure_gdf.groupby("Object ID")[attribute_name].agg(list).reset_index()
    )
    exposure_gdf.drop_duplicates(subset="Object ID", keep="first", inplace=True)
    exposure_gdf.drop(columns=attribute_name, inplace=True)
    exposure_gdf = exposure_gdf.merge(aggregated, on="Object ID")


    # Create a string from the list of values in the duplicated aggregation area 
    # column
    exposure_gdf[attribute_name] = exposure_gdf[attribute_name].apply(process_value)
        
    # Rename the 'aggregation_attribute' column to 'new_column_name'
    exposure_gdf.rename(columns={attribute_name: "BF_FID"}, inplace=True)

    return exposure_gdf

def join_exposure_bf(
    exposure_gdf: gpd.GeoDataFrame,
    building_footprint_fn: Union[str, Path],
    attribute_name: str,
    column_name: str = "BF_FID",
) -> gpd.GeoDataFrame:
    """Join building footprints to the exposure data.

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        Exposure data to join the building footprints to as "BF_FID".
    building_footprint_fn : Union[List[str], List[Path], str, Path]
        Path(s) to the building footprint.
    attribute_name : Union[List[str], str]
        Name of the building footprint ID to join.
    column_name: str = "BF_FID"
        Name of building footprint in new exposure output
    """
    exposure_gdf = join_exposure_building_footprint(exposure_gdf, building_footprint_fn, attribute_name)
    
    return exposure_gdf


def nearest_neighbor_bf(
    exposure_gdf: gpd.GeoDataFrame,
    building_footprint_fn: Union[str, Path],
    attribute_name: str,
    column_name: str = "BF_FID",
) -> gpd.GeoDataFrame:
    
    #Load new exposure dataframe
    exposure_gdf = join_exposure_bf(exposure_gdf, building_footprint_fn, attribute_name)
   
    #Load building footprint
    bf_gdf = gpd.read_file(building_footprint_fn)
   
    #merge gdf and df > is this neccessary
    merged_gdf = gis_utils.nearest_merge(exposure_gdf, bf_gdf, column_name)
    
    #Correct index
    merged_gdf["index_right"] += 1

    # Specify the columns with NaN values and the column to use for replacement
    column_with_nan = column_name  # Replace with the name of the column containing NaN values
    replacement_column = "index_right"  # Replace with the name of the column to use for replacement

    # Replace NaN values in BF_FID with values from nearest neighbour
    merged_gdf[column_with_nan].fillna(merged_gdf[replacement_column], inplace=True)

    #remove the index_right and distance_right column
    if "index_right" in merged_gdf.columns:
        del merged_gdf["index_right"]
        del merged_gdf["distance_right"]
    
    #remove geoms column to return to datafrane
    del merged_gdf["geometry"]
    

    return merged_gdf

