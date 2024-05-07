import geopandas as gpd
from typing import List, Union
from pathlib import Path

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
            how="left",
        )

        # aggregate the data if duplicates exist
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
        exposure_gdf.rename(columns={attribute_name: label_name}, inplace=True)

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
