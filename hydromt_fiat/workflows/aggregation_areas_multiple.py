import geopandas as gpd
from typing import List, Optional, Union
from pathlib import Path
import pandas as pd


# Make a function add several aggregation areas
def join_exposure_aggregation_multiple_areas(
    exposure_gdf: gpd.GeoDataFrame,
    aggregation_area_fn: Union[List[str], str, List[Path], Path],
    attribute_names: Union[List[str], str],
    label_names: Union[List[str], str],
):
    aggregation_gdf_list=[]
    for file_path in aggregation_area_fn:
        aggregation_gdf = gpd.read_file(file_path)
        aggregation_gdf_list.append(aggregation_gdf)

    ## check the projection of both gpd and if not match reproject
    #check the projection  for each gdf in list
    for index, i in enumerate(aggregation_gdf_list):
        if exposure_gdf.crs != i.crs:
            aggregation_gdf_list[index] = i.to_crs(exposure_gdf.crs)
    
   
    # join exposure currently gdf and list must be in same order > should change to if statement maybe
    # If "land use in xy gdf then use this attribute"
    resulting_dataframes = []
    count = 0
    for aggregation_gdf in aggregation_gdf_list:
        new_exposure = gpd.sjoin(
        exposure_gdf,
        aggregation_gdf[["geometry", attribute_names[count]]], 
        op='intersects',
        how="left"
    )
        resulting_dataframes.append(new_exposure)
        count = count + 1
    
       ## Rename the 'aggregation_attribute' column to 'new_column_name'
    count = 0
    for index, i in enumerate(resulting_dataframes):
        resulting_dataframes[index] = i.rename(columns={attribute_names[count]: label_names[count]})
        count = count = 1
        
    ##remove column
    for index, i in enumerate(resulting_dataframes):
        if 'index_right' in i:
            resulting_dataframes[index] = i.drop('index_right', axis=1)
    
     #Seperated gdf in a dictionary
    separated_gdf = {}
    for index, entry in enumerate(resulting_dataframes):
        key = f"gdf{index+1}"
        separated_gdf[key] = entry
    
    #create new gdf only with aggregation labels
    extracted_columns_gdf = gpd.GeoDataFrame()
    for key, gdf in separated_gdf.items():
        for column_name in gdf.columns:
            if any(label_name in column_name for label_name in label_names):
                extracted_columns_gdf[column_name] = gdf[column_name]

    #Join exposure with new geodataframe
    aggregated_exposure =exposure_gdf.join(extracted_columns_gdf)

    return aggregated_exposure
    