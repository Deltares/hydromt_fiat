import geopandas as gpd
from hydromt.gis_utils import utm_crs, nearest_merge, nearest


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


def check_geometry_type(gdf: gpd.GeoDataFrame) -> str:
    """Check if the geometry type of a GeoDataFrame is homogeneous.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        The GeoDataFrame to check.

    Raises
    ------
    ValueError
        If the geometry type of the GeoDataFrame is not homogeneous.
    """
    if len(gdf.geom_type.unique()) > 1:
        raise ValueError(
            "The geometry type of the GeoDataFrame is not homogeneous. "
            f"Geometry types found: {gdf.geom_type.unique()}"
        )
    else:
        return gdf.geom_type.unique()[0]


def get_crs_str_from_gdf(gdf_crs: gpd.GeoDataFrame.crs) -> str:
    source_data_authority = gdf_crs.to_authority()
    return source_data_authority[0] + ":" + source_data_authority[1]


def join_nearest_points(left_gdf, right_gdf, attribute_name, max_dist) -> gpd.GeoDataFrame:
    """Join two GeoDataFrames based on the nearest distance between their points.
    
    Parameters
    ----------
    left_gdf : gpd.GeoDataFrame
        The GeoDataFrame to which the data from the right GeoDataFrame will be joined.
    right_gdf : gpd.GeoDataFrame
        The GeoDataFrame from which the data will be joined to the left GeoDataFrame.
    attribute_name : str
        The name of the attribute that will be joined.
    max_dist : float
        The maximum distance for the nearest join measured in meters.

    Returns
    -------
    gpd.GeoDataFrame
        The joined GeoDataFrame.
    """    
    # Use the HydroMT function nearest_merge to join the geodataframes
    gdf_merged = nearest_merge(
        gdf1=left_gdf, gdf2=right_gdf, columns=[attribute_name], max_dist=max_dist
    )

    # Clean up the geodataframe (remove unnecessary columns)
    del gdf_merged["distance_right"]
    del gdf_merged["index_right"]
    
    return gdf_merged

    
def join_spatial_data(
    left_gdf: gpd.GeoDataFrame,
    right_gdf: gpd.GeoDataFrame,
    attribute_name: str,
    method: str,
    max_dist: float = 10,
) -> gpd.GeoDataFrame:
    """Join two GeoDataFrames based on their spatial relationship.

    Parameters
    ----------
    left_gdf : gpd.GeoDataFrame
        The GeoDataFrame to which the data from the right GeoDataFrame will be joined.
    right_gdf : gpd.GeoDataFrame
        The GeoDataFrame from which the data will be joined to the left GeoDataFrame.
    attribute_name : str
        The name of the attribute that will be joined.
    method : str
        The method that will be used to join the data. Either "nearest" or
        "intersection".
    max_dist : float, optional
        The maximum distance for the nearest join measured in meters, by default 
        10 (meters).

    Returns
    -------
    gpd.GeoDataFrame
        The joined GeoDataFrame.
    """
    left_gdf_type = check_geometry_type(left_gdf)
    right_gdf_type = check_geometry_type(right_gdf)

    if method == "nearest":
        if (left_gdf_type == "Point") and (right_gdf_type == "Point"):
            gdf = join_nearest_points(left_gdf, right_gdf, attribute_name, max_dist)
    elif method == "intersection":
        if left_gdf_type == "Polygon":
            gdf = sjoin_largest_area(left_gdf, right_gdf)
        elif left_gdf_type == "Point":
            # TODO: create a separate function for this?
            gdf = gpd.sjoin(left_gdf, right_gdf, how="left", predicate="intersects")
        else:
            raise NotImplementedError(
                f"Join method {method} is not implemented for geometry type "
                f"{left_gdf_type}"
            )
    else:
        raise NotImplementedError(f"Join method {method} is not implemented")

    # TODO: use the data from the new column to update the original column

    return gdf
