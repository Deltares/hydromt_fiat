import geopandas as gpd
from typing import List, Union
from pathlib import Path

import numpy as np

def process_value(value):
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    elif isinstance(value, list) and len(value) > 1:
        return ", ".join(value)
    else:
        return value

def spatial_joins(
    exposure_gdf: gpd.GeoDataFrame,
    areas: Union[List[str], List[Path], List[gpd.GeoDataFrame]],
    attribute_names: List[str],
    label_names: List[str],
    keep_all: bool=True,
) -> gpd.GeoDataFrame:
    """Perform spatial joins between the exposure GeoDataFrame and aggregation areas.

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        The GeoDataFrame representing the exposure data.
    areas : Union[List[str], List[Path], List[gpd.GeoDataFrame]]
        A list of aggregation areas. Each area can be specified as a file path (str or Path),
        or as a GeoDataFrame.
    attribute_names : List[str]
        A list of attribute names to be joined from the aggregation areas.
    label_names : List[str]
        A list of label names to be assigned to the joined attributes in the exposure GeoDataFrame.

    Returns
    -------
    gpd.GeoDataFrame
        The exposure GeoDataFrame with the joined attributes from the aggregation areas.

    Raises
    ------
    AssertionError
        If the specified attribute name is not found in the aggregation area.

    Notes
    -----
    - If the exposure GeoDataFrame and the aggregation area have different coordinate reference systems (CRS),
      the aggregation area will be reprojected to match the CRS of the exposure GeoDataFrame.
    - The function performs a spatial join using the 'intersects' predicate.
    - If duplicates exist in the joined data, the function aggregates the data by grouping on the 'Object ID'
      column and creating a list of values for each attribute.
    - The function expects the order of the label names to match the order of the aggregation areas in the 'areas'
      parameter.

    """
    
    filtered_areas = []
    
    for area, attribute_name, label_name in zip(areas, attribute_names, label_names):

        if isinstance(area, str) or isinstance(area, Path):
            area_gdf = gpd.read_file(area)
        else:
            area_gdf = area

        ## check the projection of both gdf and if not match, reproject
        if exposure_gdf.crs != area_gdf.crs:
            area_gdf = area_gdf.to_crs(exposure_gdf.crs)

        assert attribute_name in area_gdf.columns, f"Attribute {attribute_name} not found in {area}"
        
        # Keep only used column
        area_gdf = area_gdf[[attribute_name, "geometry"]].reset_index(drop=True)
        
        # If you overwrite the exposure_gdf with the joined data, you can append all 
        # aggregation areas to the same exposure_gdf
        exposure_gdf = gpd.sjoin(
            exposure_gdf,
            area_gdf,
            predicate="intersects",
            how="left",
        )
        # If we want to keep only used area we filter based on the intersections else we provide the whole dataframe
        if not keep_all:
            inds = np.sort(exposure_gdf["index_right"].dropna().unique())
            # TODO instead of keeping the ones that are joined keep everything that overlaps with the region?
            filtered_areas.append(area_gdf.iloc[inds].reset_index(drop=True))
        else:
            filtered_areas.append(area_gdf)
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

    return exposure_gdf, filtered_areas


def join_exposure_aggregation_areas(
    exposure_gdf: gpd.GeoDataFrame,
    aggregation_area_fn: Union[List[str], List[Path], List[gpd.GeoDataFrame], str, Path, gpd.GeoDataFrame],
    attribute_names: Union[List[str], str],
    label_names: Union[List[str], str],
    keep_all: bool=True
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
    
    exposure_gdf, areas_gdf = spatial_joins(exposure_gdf, aggregation_area_fn, attribute_names, label_names, keep_all)
    
    # Remove the geometry column from the exposure_gdf to return a dataframe
    del exposure_gdf["geometry"]
    
    return exposure_gdf, areas_gdf
