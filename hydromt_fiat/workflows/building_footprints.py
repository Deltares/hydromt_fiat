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

    ## check the projection of both gdf and if not match, reproject
    if exposure_gdf.crs != bf_gdf.crs:
        bf_gdf = bf_gdf.to_crs(exposure_gdf.crs)

      
    assert attribute_name in bf_gdf.columns, f"Attribute {attribute_name} not found in {building_footprint_fn}"
    
    #Check for unique BF-FID
    assert bf_gdf[attribute_name].is_unique, f"Building footprint ID returns duplicates. Building footprint ID should be unique."

    #Create fully merged gdf
    #merged_gdf = gis_utils.nearest_merge(bf_gdf,exposure_gdf)

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
        
    # Rename the 'aggregation_attribute' column to 'new_column_name'. Put in 
    # Documentation that the order the user put the label name must be the order of the gdf
    exposure_gdf.rename(columns={attribute_name: "BF_FID"}, inplace=True)

    ##remove the index_right column
    if "index_right" in exposure_gdf.columns:
        del exposure_gdf["index_right"]

    return exposure_gdf


def join_exposure_bf(
    exposure_gdf: gpd.GeoDataFrame,
    building_footprint_fn: Union[str, Path],
    attribute_names: str,
    column_name: str = "BF_FID",
) -> gpd.GeoDataFrame:
    """Join building footprints to the exposure data.

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        Exposure data to join the building footprints to as "BF_FID".
    building_footprint_fn : Union[List[str], List[Path], str, Path]
        Path(s) to the building footprint.
    attribute_names : Union[List[str], str]
        Name of the building footprint ID to join.
    column_name: str = "BF_FID"
        Name of building footprint in new exposure output
    """
    exposure_gdf = join_exposure_building_footprint(exposure_gdf, building_footprint_fn, attribute_names)
    
    # Remove the geometry column from the exposure_gdf to return a dataframe
    del exposure_gdf["geometry"]
    
    return exposure_gdf


def nearest_neighbor_bf(
    exposure_gdf: gpd.GeoDataFrame,
    building_footprint_fn: Union[str, Path],
    attribute_names: str,
    column_name: str = "BF_FID",
) -> gpd.GeoDataFrame:
    
    #this should be a dataframe
    exposure_df = join_exposure_bf(exposure_gdf, building_footprint_fn, attribute_names)
   
    #Load buildings.gpkg
    exposure_gdf= gpd.read_file(Path(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\HydroMT\Issue_Solving\#133\testcase_data\exposure\buildings.gpkg"))

    
    #Mhere all good
    #exposure_df= pd.read_csv(Path(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\HydroMT\Issue_Solving\#133\output\exposure\exposure.csv"))
    #exposure_gdf= gpd.read_file(Path(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\HydroMT\Issue_Solving\#133\output\exposure\buildings.gpkg"))

    
    merged_gdf_multiple = exposure_gdf.merge(exposure_df, left_on='Object ID', right_on='Object ID', how='inner')
    bf_gdf = gpd.read_file(building_footprint_fn)
    #same as above only absolute path : bf_gdf = gpd.read_file(Path(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\HydroMT\Issue_Solving\#133\testcase_data\building_footprints\building_footprint.gpkg"))
    
    merged_gdf = gis_utils.nearest_merge(merged_gdf_multiple, bf_gdf, "BF_FID")
    merged_gdf.to_file(Path(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\HydroMT\Issue_Solving\#133\testcase_data\building_footprints\test.gpkg"))
    value =1
    
    merged_gdf["index_right"] += value

    # Specify the columns with NaN values and the column to use for replacement
    column_with_nan = "BF_FID"  # Replace with the name of the column containing NaN values
    replacement_column = "index_right"  # Replace with the name of the column to use for replacement

    # Use the fillna method to replace NaN values in column1 with values from column2
    merged_gdf[column_with_nan].fillna(merged_gdf[replacement_column], inplace=True)

     ##remove the index_right column
    if "index_right" in merged_gdf.columns:
        del merged_gdf["index_right"]
    
    del merged_gdf["geometry"]

    return merged_gdf

