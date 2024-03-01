import geopandas as gpd
from typing import List, Union
from pathlib import Path
import pandas as pd
import numpy as np

def process_value(value):
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    elif isinstance(value, list) and len(value) > 1:
        return ", ".join(value)
    else:
        return value

def join_exposure_aggregation_multiple_areas(
    exposure_gdf: gpd.GeoDataFrame,
    aggregation_area_fn: Union[List[str], List[Path], List[gpd.GeoDataFrame]],
    attribute_names: List[str],
    label_names: List[str],
) -> gpd.GeoDataFrame:
    """_summary_

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        _description_
    aggregation_area_fn : Union[List[str], List[Path]]
        _description_
    attribute_names : List[str]
        _description_
    label_names : List[str]
        _description_

    Returns
    -------
    gpd.GeoDataFrame
        _description_
    """
    for file_path, attribute_name, label_name in zip(aggregation_area_fn, attribute_names, label_names):

        if isinstance(file_path, str) or isinstance(file_path, Path):
            aggregation_gdf = gpd.read_file(file_path)
        else:
            aggregation_gdf = file_path

        ## check the projection of both gdf and if not match, reproject
        if exposure_gdf.crs != aggregation_gdf.crs:
            aggregation_gdf = aggregation_gdf.to_crs(exposure_gdf.crs)

            
        assert attribute_name in aggregation_gdf.columns, f"Attribute {attribute_name} not found in {file_path}"

        # If you overwrite the exposure_gdf with the joined data, you can append all 
        # aggregation areas to the same exposure_gdf
       
        exposure_gdf = gpd.sjoin(
            exposure_gdf,
            aggregation_gdf[["geometry", attribute_name]],
            predicate="intersects",
            how="left")

        # aggregate the data if duplicates exist
        aggregated = (
            exposure_gdf.groupby("Object ID")[attribute_name].agg(list).reset_index()
        )
        exposure_gdf.drop_duplicates(subset="Object ID", keep="first", inplace=True)

        if len(aggregated[attribute_name].values.any()) >= 2:
            # If new composite area falls in multiple aggregation zones should do an overlay function and where they overlay, split the composite area into
            # polygons and assign the aggregation area
            new_exposure_gdf = exposure_gdf.rename(columns = {attribute_name: "pot"})
            res_intersection = new_exposure_gdf.overlay(aggregation_gdf[[attribute_name, 'geometry']], how='intersection')
            res_intersection.drop(["index_right", "pot"], axis = 1, inplace = True)

            # exposure area - res_intersection = left over shape in no zone 
            exposure_outside_aggregation = new_exposure_gdf.overlay(res_intersection[["geometry"]], how = "symmetric_difference")
            exposure_outside_aggregation.drop(["index_right", "pot"], axis = 1, inplace = True)
            exposure_outside_aggregation = exposure_outside_aggregation.dropna()

            # Combine divided objects of new composite area within aggregation zone and outside #TODO create OBJECT IDs
            exposure_gdf = pd.concat([res_intersection, exposure_outside_aggregation], ignore_index=True)
            idx_duplicates = exposure_gdf.index[exposure_gdf.duplicated("Object ID") == True]
            exposure_gdf["Object ID"] = exposure_gdf["Object ID"].astype(int)
            exposure_gdf.loc[idx_duplicates, "Object ID"] = np.random.choice(range(exposure_gdf["Object ID"].values.max() + 1 ,exposure_gdf["Object ID"].values.max() +1 + len(idx_duplicates)), size=len(idx_duplicates), replace=False)
            
            
            # Create an empty GeoDataFrame and append the exposure data
            try:
                new_exposure_aggregation
            except NameError:
                data = pd.DataFrame(columns=['geometry'])
                final_exposure = gpd.GeoDataFrame(data, geometry='geometry')
                new_exposure_aggregation = pd.concat([final_exposure, exposure_gdf], ignore_index=True) 
                exposure_gdf = new_exposure_aggregation
            else:
                exposure_gdf = pd.concat([new_exposure_aggregation, exposure_gdf], ignore_index=True)            
        else:
            exposure_gdf.drop(columns=attribute_name, inplace=True)
            exposure_gdf = exposure_gdf.merge(aggregated, on="Object ID")

            # Create a string from the list of values in the duplicated aggregation area 
            # column
            exposure_gdf[attribute_name] = exposure_gdf[attribute_name].apply(process_value)
                
            # Rename the 'aggregation_attribute' column to 'new_column_name'. Put in 
            # Documentation that the order the user put the label name must be the order of the gdf
            exposure_gdf.rename(columns={attribute_name: label_name}, inplace=True)
            
            exposure_gdf
            ##remove the index_right column
            if "index_right" in exposure_gdf.columns:
                del exposure_gdf["index_right"]

    return exposure_gdf


def join_exposure_aggregation_areas(
    exposure_gdf: gpd.GeoDataFrame,
    aggregation_area_fn: Union[List[str], List[Path], List[gpd.GeoDataFrame], str, Path, gpd.GeoDataFrame],
    attribute_names: Union[List[str], str],
    label_names: Union[List[str], str],
) -> gpd.GeoDataFrame:
    """Join aggregation area labels to the exposure data.

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        Exposure data to join the aggregation areas to as `label_names`.
    aggregation_area_fn : Union[List[str], List[Path], str, Path]
        Path(s) to the aggregation area(s).
    attribute_names : Union[List[str], str]
        Name of the attribute(s) to join.
    label_names : Union[List[str], str]
        Name of the label(s) to join.
    """
    if isinstance(aggregation_area_fn, str) or isinstance(aggregation_area_fn, Path) or isinstance(aggregation_area_fn, gpd.GeoDataFrame):
        aggregation_area_fn = [aggregation_area_fn]
    if isinstance(attribute_names, str):
        attribute_names = [attribute_names]
    if isinstance(label_names, str):
        label_names = [label_names]
    
    exposure_gdf = join_exposure_aggregation_multiple_areas(exposure_gdf, aggregation_area_fn, attribute_names, label_names)
    
    # Remove the geometry column from the exposure_gdf to return a dataframe
    del exposure_gdf["geometry"]
    return exposure_gdf
