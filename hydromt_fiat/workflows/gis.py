import geopandas as gpd
from hydromt.gis_utils import utm_crs


def get_area(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Adds an area column to a GeoDataFrame.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        The GeoDataFrame to which the area column will be added.

    Returns
    -------
    gpd.GeoDataFrame
        The GeoDataFrame with an additional column "area".
    """
    # Calculate the area of each object
    if gdf.crs.is_geographic:
        # If the CRS is geographic, reproject to the nearest UTM zone
        nearest_utm = utm_crs(gdf.total_bounds)
        gdf_utm = gdf.to_crs(nearest_utm)
        gdf["area"] = gdf_utm["geometry"].area
    elif gdf.crs.is_projected:
        # If the CRS is projected, calculate the area in the same CRS
        gdf["area"] = gdf["geometry"].area
    return gdf


def sjoin_largest_area(
    left_gdf: gpd.GeoDataFrame, right_gdf: gpd.GeoDataFrame, id_col: str = "Object ID"
) -> gpd.GeoDataFrame:
    """Spatial join of two GeoDataFrames, keeping only the joined data from the largest
    intersection per object.

    Parameters
    ----------
    left_gdf : gpd.GeoDataFrame
        The GeoDataFrame to which the data from the right GeoDataFrame will be joined.
    right_gdf : gpd.GeoDataFrame
        The GeoDataFrame from which the data will be joined to the left GeoDataFrame.
    id_col : str, optional
        The ID column that will be used to drop the duplicates from overlapping
        geometries, by default "Object ID"

    Returns
    -------
    gpd.GeoDataFrame
        Resulting GeoDataFrame with the joined data from the largest intersection per
        object.
    """
    gdf = gpd.overlay(left_gdf, right_gdf, how="intersection")
    gdf["area"] = gdf.geometry.area
    gdf.sort_values(by="area", inplace=True)
    gdf.drop_duplicates(subset=id_col, keep="last", inplace=True)
    gdf.drop(columns=["area"], inplace=True)
    return gdf


def get_crs_str_from_gdf(gdf_crs: gpd.GeoDataFrame.crs) -> str:
    source_data_authority = gdf_crs.to_authority()
    return source_data_authority[0] + ":" + source_data_authority[1]