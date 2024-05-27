import geopandas as gpd
from typing import List, Union
from pathlib import Path
import pandas as pd
import numpy as np

def process_value(value):
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    elif isinstance(value, list) and len(value) > 1:
        return int(value[0])
    else:
        return value

def join_exposure_aggregation_multiple_areas(
    exposure_gdf: gpd.GeoDataFrame,
    aggregation_area_fn: Union[List[str], List[Path], List[gpd.GeoDataFrame]],
    attribute_names: List[str],
    label_names: List[str],
    new_composite_area: bool
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
    new_composite_area : bool
        _description_

    Returns
    -------
    gpd.GeoDataFrame
        _description_
    """
    exposure_gdf_copy = exposure_gdf.copy()
    
    # Create column to assign new composite area ID
    if new_composite_area[0]:
        exposure_gdf["ca_ID"] = range(0,len(exposure_gdf),1)

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

        ##remove the index_right column
        if "index_right" in exposure_gdf.columns:
            del exposure_gdf["index_right"]

        # aggregate the data if duplicates exist
        aggregated = (
            exposure_gdf.groupby("Object ID")[attribute_name].agg(list).reset_index()
        )
        exposure_gdf.drop_duplicates(subset="Object ID", keep="first", inplace=True)
        
        # Check if new gdf was already created in previous loop
        try:
            new_exposure_aggregation
        except NameError:
            new_exposure_aggregation = None
        else:
            new_exposure_aggregation = new_exposure_aggregation

        if new_composite_area[0]:
            new_exposure_aggregation, exposure_gdf = split_composite_area(exposure_gdf, aggregation_gdf, attribute_name, new_exposure_aggregation)     

        else:
            exposure_gdf.drop(columns=attribute_name, inplace=True)
            exposure_gdf = exposure_gdf.merge(aggregated, on="Object ID")

            # Create a string from the list of values in the duplicated aggregation area and keep the first
            exposure_gdf[attribute_name] = exposure_gdf[attribute_name].apply(process_value)
            
            ##remove the index_right column
            if "index_right" in exposure_gdf.columns:
                del exposure_gdf["index_right"]
        
        # Rename the 'aggregation_attribute' column to 'new_column_name'. Put in 
        # Documentation that the order the user put the label name must be the order of the gdf
        exposure_gdf.rename(columns={attribute_name: label_name}, inplace=True)
    
    total_area = exposure_gdf.geometry.area.sum()
    filter_percentage = 0.0001
    area_threshold = total_area * filter_percentage
    exposure_gdf = exposure_gdf[exposure_gdf.geometry.area >= area_threshold]

    # Split Maximum Potential Damages
    if new_composite_area[0]:
        exposure_max_potential_damage_struct = list(exposure_gdf_copy["Max Potential Damage: Structure"].values)
        exposure_max_potential_damage_cont = list(exposure_gdf_copy["Max Potential Damage: Content"].values)
        exposure_gdf = split_max_damages_new_composite_area(exposure_gdf, exposure_max_potential_damage_struct, exposure_max_potential_damage_cont)
    
    return exposure_gdf

def split_composite_area(exposure_gdf, aggregation_gdf, attribute_name, new_exposure_aggregation):
    
    if any(
    exposure_geometry.intersects(aggregation_geometry)
    for exposure_geometry in exposure_gdf.geometry
    for aggregation_geometry in aggregation_gdf.geometry):
        # Split exposure_gdf by aggregation zone 
        new_exposure_gdf = exposure_gdf.rename(columns = {attribute_name: "pot"})
        res_intersection = new_exposure_gdf.overlay(aggregation_gdf[[attribute_name, 'geometry']], how='intersection')
        res_intersection.drop("pot", axis = 1, inplace = True)

        # Grab the area that falls in no zone 
        exposure_outside_aggregation = new_exposure_gdf.overlay(res_intersection[["geometry"]], how = "symmetric_difference")
        exposure_outside_aggregation.drop("pot", axis = 1, inplace = True)

        # Combine divided objects of new composite area with areas that fall in no zone 
        exposure_gdf = pd.concat([res_intersection, exposure_outside_aggregation], ignore_index=True) 
        exposure_gdf.dropna(subset = [ "Object ID"] , inplace =True)

        # Explode Multipolygons
        exposure_gdf = exposure_gdf.explode().reset_index()
        idx_multiploygon = exposure_gdf[exposure_gdf['geometry'].area < 1e-10].index
        if not idx_multiploygon.empty:
            exposure_gdf.drop(idx_multiploygon, inplace = True)
        exposure_gdf.drop(["level_0", "level_1"], axis = 1, inplace = True)

        # create new Object IDs       
        exposure_gdf["Object ID"] = exposure_gdf["Object ID"].astype(int)
        init_Object_ID = exposure_gdf.loc[0,"Object ID"]
        exposure_gdf.loc[0:, "Object ID"] = np.arange(init_Object_ID + 1 , init_Object_ID + 1 + int(len(exposure_gdf)), 1).tolist()

    # Create an empty GeoDataFrame and append the exposure data
    if new_exposure_aggregation is None:
        data = pd.DataFrame(columns=['geometry'])
        final_exposure = gpd.GeoDataFrame(data, geometry='geometry')
        new_exposure_aggregation = pd.concat([final_exposure, exposure_gdf], ignore_index=True) 
        exposure_gdf = new_exposure_aggregation
    else: 
        new_exposure_aggregation = exposure_gdf
    
    # Remove the index_right column
    if "index_right" in exposure_gdf.columns:
        del exposure_gdf["index_right"]  

    return new_exposure_aggregation, exposure_gdf

def split_max_damages_new_composite_area(
        exposure_gdf: gpd.GeoDataFrame,
        exposure_max_potential_damage_struct: Union[float, int, List[Union[float, int]]], 
        exposure_max_potential_damage_cont: Union[float, int, List[Union[float, int]]]
        ) -> gpd.GeoDataFrame:
    """Split the max potential damages by area size

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        Exposure data to split the max potential damages.
    exposure_max_potential_damage_struct: Union[int, List[int]]
        Max potential damage: Structure of new composite area per polygon. In case of multiple polygons, multiple max potential damages
    exposure_max_potential_damage_cont: Union[int, List[int]]
        Max potential damage: Content of new composite area per polygon. In case of multiple polygons, multiple max potential damages
    """
    new_composite_areas_struct = []
    new_composite_areas_cont = []
    
    #Caculate area per new composite area ID
    area_by_id = exposure_gdf.groupby('ca_ID')['geometry'].apply(lambda x: x.area.sum()).reset_index()
    exposure_total_area = area_by_id['geometry'].tolist()
    
    for exposure_total_area, exposure_max_potential_damage_struct,exposure_max_potential_damage_cont in zip(exposure_total_area, exposure_max_potential_damage_struct, exposure_max_potential_damage_cont):

        # Calculate relative Max Potential Damages for Structure and Content based on area
        filtered_exposure_gdf_struct = exposure_gdf[exposure_gdf["Max Potential Damage: Structure"] == exposure_max_potential_damage_struct]
        for index, row in filtered_exposure_gdf_struct.iterrows():
            filtered_exposure_gdf_struct.at[index,"rel_area"] = row.geometry.area / exposure_total_area
            filtered_exposure_gdf_struct.at[index, "rel_max_pot_damages_struct"] = (filtered_exposure_gdf_struct.at[index,"rel_area"] * exposure_max_potential_damage_struct)
        
        filtered_exposure_gdf_cont = exposure_gdf[exposure_gdf["Max Potential Damage: Content"] == exposure_max_potential_damage_cont]
        for index, row in filtered_exposure_gdf_cont .iterrows():
            filtered_exposure_gdf_cont.at[index,"rel_area"] = row.geometry.area / exposure_total_area
            filtered_exposure_gdf_cont.at[index, "rel_max_pot_damages_cont"] = (filtered_exposure_gdf_cont.at[index,"rel_area"] * exposure_max_potential_damage_cont)

        filtered_exposure_gdf_struct["Max Potential Damage: Structure"] = filtered_exposure_gdf_struct["rel_max_pot_damages_struct"]
        filtered_exposure_gdf_cont["Max Potential Damage: Content"] = filtered_exposure_gdf_cont["rel_max_pot_damages_cont"]
        filtered_exposure_gdf_struct.drop(columns = ["rel_max_pot_damages_struct", "rel_area"], inplace = True)
        filtered_exposure_gdf_cont.drop(columns = ["rel_max_pot_damages_cont", "rel_area"], inplace = True)
        
        # Add all gdfs to a list 
        new_composite_areas_struct.append(filtered_exposure_gdf_struct)
        new_composite_areas_cont.append(filtered_exposure_gdf_cont)
   
   # Combine all individual new composite areas back to one gdf for each Damage Type
    exposure_gdf_struct = pd.concat(new_composite_areas_struct, ignore_index = True)
    exposure_gdf_cont = pd.concat(new_composite_areas_cont, ignore_index = True)
    
    # Combine Damage Type gdfs to one gdf
    exposure_gdf = exposure_gdf_struct.merge(exposure_gdf_cont[["Object ID", "Max Potential Damage: Content"]], on = "Object ID", how = "left")
    exposure_gdf["Max Potential Damage: Content_x"] = exposure_gdf["Max Potential Damage: Content_y"]
    exposure_gdf.drop("Max Potential Damage: Content_y", axis =1, inplace = True)
    exposure_gdf = exposure_gdf.rename(columns= {"Max Potential Damage: Content_x": "Max Potential Damage: Content"})
    
    del exposure_gdf["ca_ID"]
    
    return exposure_gdf

def join_exposure_aggregation_areas(
    exposure_gdf: gpd.GeoDataFrame,
    aggregation_area_fn: Union[List[str], List[Path], List[gpd.GeoDataFrame], str, Path, gpd.GeoDataFrame],
    attribute_names: Union[List[str], str],
    label_names: Union[List[str], str],
    new_composite_area: bool,
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
    new_composite_area : bool
        Check whether aggregation is done for a new composite area.
    """
    if isinstance(aggregation_area_fn, str) or isinstance(aggregation_area_fn, Path) or isinstance(aggregation_area_fn, gpd.GeoDataFrame):
        aggregation_area_fn = [aggregation_area_fn]
    if isinstance(attribute_names, str):
        attribute_names = [attribute_names]
    if isinstance(label_names, str):
        label_names = [label_names]
    if isinstance(new_composite_area, bool):
        new_composite_area = [new_composite_area]

    exposure_gdf = join_exposure_aggregation_multiple_areas(exposure_gdf, aggregation_area_fn, attribute_names, label_names, new_composite_area)
    
    # Remove the geometry column from the exposure_gdf to return a dataframe
    exposure_geoms = exposure_gdf[["Object ID", "geometry"]]

    del exposure_gdf["geometry"]

    return exposure_gdf, exposure_geoms 
