import geopandas as gpd
from typing import List, Optional, Union
from pathlib import Path


# Make a function add aggregation area
def join_exposure_aggregation_area(
    exposure_gdf: gpd.GeoDataFrame,
    aggregation_area_fn: Union[str, Path],
    attribute_names: str,
    label_names: str,
):
    aggregation_gdf = gpd.read_file(aggregation_area_fn)

    # check the projection of both gpd and if not match reproject
    if exposure_gdf.crs != aggregation_gdf.crs:
        aggregation_gdf = aggregation_gdf.to_crs(exposure_gdf.crs)

    # join exposure
    new_exposure = gpd.sjoin(
        exposure_gdf,
        aggregation_gdf[["geometry", attribute_names]],
        op="intersects",
        how="left",
    )
    # Rename the 'aggregation_attribute' column to 'new_column_name'
    new_exposure = new_exposure.rename(columns={attribute_names: label_names})
    
    #remove column
    if 'index_right' in new_exposure.columns:
        new_exposure = new_exposure.drop('index_right', axis=1)
    
    return new_exposure



