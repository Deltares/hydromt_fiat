import geopandas as gpd
from typing import List, Union
from pathlib import Path

def process_value(value):
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    elif isinstance(value, list) and len(value) > 1:
        return ", ".join(value)
    else:
        return value

def join_exposure_building_footprint(
    exposure_gdf: gpd.GeoDataFrame,
    building_footprint_fn: Union[List[str], List[Path]],
    attribute_names: List[str],
) -> gpd.GeoDataFrame:
    """_summary_

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        _description_
    building_footprint_fn : Union[List[str], List[Path]]
        _description_
    attribute_names : List[str]
        _description_


    Returns
    -------
    gpd.GeoDataFrame
        _description_
    """
    for file_path, attribute_name in zip(building_footprint_fn, attribute_names):
        bf_gdf = gpd.read_file(file_path)

        ## check the projection of both gdf and if not match, reproject
        if exposure_gdf.crs != bf_gdf.crs:
            bf_gdf = bf_gdf.to_crs(exposure_gdf.crs)

            
        assert attribute_name in bf_gdf.columns, f"Attribute {attribute_name} not found in {file_path}"

        # If you overwrite the exposure_gdf with the joined data, you can append all 
        # aggregation areas to the same exposure_gdf
        exposure_gdf = gpd.sjoin(
            exposure_gdf,
            bf_gdf[["geometry", attribute_name]],
            op="intersects",
            how="left",
        )

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
    building_footprint_fn: Union[List[str], List[Path], str, Path],
    attribute_names: Union[List[str], str],
) -> gpd.GeoDataFrame:
    """Join aggregation area labels to the exposure data.

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        Exposure data to join the aggregation areas to as "Aggregation 
        Label: `label_names`".
    building_footprint_fn : Union[List[str], List[Path], str, Path]
        Path(s) to the aggregation area(s).
    attribute_names : Union[List[str], str]
        Name of the attribute(s) to join.
    
    """
    if isinstance(building_footprint_fn, str) or isinstance(building_footprint_fn, Path):
        building_footprint_fn = [building_footprint_fn]
    if isinstance(attribute_names, str):
        attribute_names = [attribute_names]
    
    exposure_gdf = join_exposure_building_footprint(exposure_gdf, building_footprint_fn, attribute_names)
    
    # Remove the geometry column from the exposure_gdf to return a dataframe
    del exposure_gdf["geometry"]
    return exposure_gdf
