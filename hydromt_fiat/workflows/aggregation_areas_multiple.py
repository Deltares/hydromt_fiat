import geopandas as gpd
from typing import List, Optional, Union
from pathlib import Path

# Make a function add several aggregation areas
def join_exposure_aggregation_multiple_areas(
    exposure_gdf: gpd.GeoDataFrame,
    aggregation_area_fn: Union[List[str], str, List[Path], Path],
    attribute_names: Union[List[str], str],
    label_names: Union[List[str], str],
):
    for values in aggregation_area_fn:
        aggregation_gdf = gpd.read_file(values, aggregation_area_fn)

    ## check the projection of both gpd and if not match reproject
    #if exposure_gdf.crs != aggregation_gdf.crs:
    #    aggregation_gdf = aggregation_gdf.to_crs(exposure_gdf.crs)

    # join exposure
    new_exposure = gpd.sjoin(
        exposure_gdf,
        aggregation_gdf[["geometry", attribute_names]],
        op="intersects",
        how="left",
    )
    ## Rename the 'aggregation_attribute' column to 'new_column_name'
    #new_exposure = new_exposure.rename(columns={attribute_names: label_names})
    
    ##remove column
    #if 'index_right' in new_exposure.columns:
        #new_exposure = new_exposure.drop('index_right', axis=1)
    
    return new_exposure