import geopandas as gpd
from typing import Union
from pathlib import Path


def process_value(value):
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    elif isinstance(value, list) and len(value) > 1:
        return ", ".join([str(val) for val in value if isinstance(val, int)])
    else:
        return value


def join_exposure_building_footprints(
    exposure_gdf: gpd.GeoDataFrame,
    building_footprint_fn: Union[str, Path],
    attribute_name: str,
    column_name: str = "BF_FID",
) -> gpd.GeoDataFrame:
    """Join building footprints to the exposure data.

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
        An updated exposure GeoDataFrame including the building footprints.
    """
    # Read the building footprints file
    bf_gdf = gpd.read_file(building_footprint_fn)

    # Check if the attribute is in the building footprint file
    assert (
        attribute_name in bf_gdf.columns
    ), f"Attribute {attribute_name} not found in {building_footprint_fn}"

    # Check for unique identifier attribute
    assert bf_gdf[
        attribute_name
    ].is_unique, "Building footprint ID returns duplicates. Building footprint ID (attribute_name) should be unique."

    # Change the column type to be an integer
    bf_gdf[attribute_name] = bf_gdf[attribute_name].astype("int")

    # check the projection of both gdf and if not match, reproject
    if exposure_gdf.crs != bf_gdf.crs:
        bf_gdf = bf_gdf.to_crs(exposure_gdf.crs)

    # Spatially join the exposure and building footprint data
    joined_gdf = gpd.sjoin(
        exposure_gdf,
        bf_gdf[["geometry", attribute_name]],
        predicate="intersects",
        how="right",
    )

    # Aggregate the data if duplicates exist
    aggregated = joined_gdf.groupby("object_id")[attribute_name].agg(list).reset_index()
    exposure_gdf = exposure_gdf.merge(aggregated, on="object_id", how="left")

    # Create a string from the list of values in the duplicated aggregation area
    # column
    exposure_gdf[attribute_name] = exposure_gdf[attribute_name].apply(process_value)

    # Rename the 'aggregation_attribute' column to 'new_column_name'
    exposure_gdf.rename(columns={attribute_name: column_name}, inplace=True)

    return exposure_gdf
