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
    aggregation_gdf_list = []
    for file_path in aggregation_area_fn:
        aggregation_gdf = gpd.read_file(file_path)
        aggregation_gdf_list.append(aggregation_gdf)

    ## check the projection of both gpd and if not match reproject
    for index, i in enumerate(aggregation_gdf_list):
        if exposure_gdf.crs != i.crs:
            aggregation_gdf_list[index] = i.to_crs(exposure_gdf.crs)

        # join exposure currently gdf and list must be in same order
        resulting_dataframes = []

        selected_column = None
        for aggregation_gdf in aggregation_gdf_list:
            for column_name in aggregation_gdf.columns:
                if any(label_name in column_name for label_name in attribute_names):
                    selected_column = column_name
            new_exposure = gpd.sjoin(
                exposure_gdf,
                aggregation_gdf[["geometry", selected_column]],
                op="intersects",
                how="left",
            )
            resulting_dataframes.append(new_exposure)

        ## Rename the 'aggregation_attribute' column to 'new_column_name'. Put in Documentation that the order the user put the label name must be the order of the gdf
        count = 0
        for gdf in resulting_dataframes:
            for column_name in gdf.columns:
                if any(label_name in column_name for label_name in attribute_names):
                    new_column_name = label_names[count]
                    gdf.rename(columns={column_name: new_column_name}, inplace=True)
            count += 1

        ##remove column
        for index, i in enumerate(resulting_dataframes):
            if "index_right" in i:
                resulting_dataframes[index] = i.drop("index_right", axis=1)

        # Seperated gdf in a dictionary
        separated_gdf = {}
        for index, entry in enumerate(resulting_dataframes):
            key = f"gdf{index+1}"
            separated_gdf[key] = entry

        # create new gdf only with aggregation labels
        extracted_columns_gdf = gpd.GeoDataFrame()
        for key, gdf in separated_gdf.items():
            for column_name in gdf.columns:
                if any(label_name in column_name for label_name in label_names):
                    extracted_columns_gdf[column_name] = gdf[column_name]

    # Join exposure with new geodataframe
    aggregated_exposure = exposure_gdf.join(extracted_columns_gdf)

    return aggregated_exposure
