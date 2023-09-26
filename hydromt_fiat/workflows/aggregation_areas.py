import geopandas as gpd
from typing import Union
from pathlib import Path

# Make a function add aggregation area
def join_exposure_aggregation_area(
    exposure_gdf: gpd.GeoDataFrame, aggregation_source: Union[str,Path], aggregation_attribute: str
):
    aggregation_gdf = gpd.read_file(aggregation_source)
    
    # check the projection of both gpd and if not match reproject
    if exposure_gdf.crs != aggregation_gdf.crs:
        aggregation_gdf = aggregation_gdf.to_crs(exposure_gdf.crs)

    # join exposure
    new_exposure = gpd.sjoin(
        exposure_gdf,
        aggregation_gdf[["geometry", aggregation_attribute]],
        op="intersects",
        how="left",
    )

    return new_exposure
