import geopandas as gpd
from hydromt.gis_utils import utm_crs, nearest_merge
from typing import List, Union
import logging
import rasterio
from rasterio.features import rasterize
from xrspatial import zonal_stats
import pandas as pd
import numpy as np
import xarray as xr
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time


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
    left_gdf: gpd.GeoDataFrame, right_gdf: gpd.GeoDataFrame, id_col: str = "object_id"
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
        geometries, by default "object_id"

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


def clean_up_gdf(gdf: gpd.GeoDataFrame, columns: List[str]) -> gpd.GeoDataFrame:
    """Clean up a GeoDataFrame by removing unnecessary columns.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        The GeoDataFrame to clean up.

    Returns
    -------
    gpd.GeoDataFrame
        The cleaned up GeoDataFrame.
    """
    # Remove unnecessary columns
    for col in columns:
        del gdf[col]

    return gdf


def join_nearest_points(
    left_gdf: gpd.GeoDataFrame,
    right_gdf: gpd.GeoDataFrame,
    attribute_name: str,
    max_dist: float,
) -> gpd.GeoDataFrame:
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
    gdf_merged = clean_up_gdf(gdf_merged, ["distance_right", "index_right"])

    return gdf_merged


def intersect_points_polygons(left_gdf, right_gdf, attribute_name) -> gpd.GeoDataFrame:
    gdf_merged = gpd.sjoin(left_gdf, right_gdf, how="left", predicate="intersects")

    # Clean up the geodataframe (remove unnecessary columns)
    gdf_merged = clean_up_gdf(gdf_merged, ["index_right"])

    return gdf_merged

def process_multipolygon(gdf):
    if 'MultiPolygon' in list(gdf.geom_type.unique()):
        for index, row in gdf.iterrows():
            if row['geometry'].geom_type == "MultiPolygon":
                largest_polygon = max(row['geometry'].geoms, key=lambda a: a.area)
                gdf.at[index, 'geometry'] = largest_polygon
        assert len(gdf.geom_type.unique()) == 1

def join_spatial_data(
    left_gdf: gpd.GeoDataFrame,
    right_gdf: gpd.GeoDataFrame,
    attribute_name: str,
    method: str,
    max_dist: float = 10,
    logger: logging.Logger = None,
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
    logger : logging.Logger
        A logger object.

    Returns
    -------
    gpd.GeoDataFrame
        The joined GeoDataFrame.
    """
    try:
        assert left_gdf.crs == right_gdf.crs, (
            "The CRS of the GeoDataFrames to join do not match. "
            f"Left CRS: {get_crs_str_from_gdf(left_gdf.crs)}, "
            f"Right CRS: {get_crs_str_from_gdf(right_gdf.crs)}"
        )
    except AssertionError as e:
        logger.warning(e)
        logger.warning(
            "Reprojecting the GeoDataFrame from "
            f"{get_crs_str_from_gdf(right_gdf.crs)} to "
            f"{get_crs_str_from_gdf(left_gdf.crs)}."
        )
        right_gdf = right_gdf.to_crs(left_gdf.crs)

    # Process both left_gdf and right_gdf
    process_multipolygon(left_gdf)
    process_multipolygon(right_gdf)

    left_gdf_type = check_geometry_type(left_gdf)
    right_gdf_type = check_geometry_type(right_gdf)

    assert (left_gdf_type == "Polygon") or (
        left_gdf_type == "Point"
    ), "The left GeoDataFrame should contain either polygons or points."

    assert (right_gdf_type == "Polygon") or (
        right_gdf_type == "Point"
    ), "The right GeoDataFrame should contain either polygons or points."

    if method == "nearest":
        if left_gdf_type == "Polygon":
            left_gdf.geometry = left_gdf.geometry.centroid

        if right_gdf_type == "Polygon":
            right_gdf.geometry = right_gdf.geometry.centroid

        gdf = join_nearest_points(left_gdf, right_gdf, attribute_name, max_dist)

    elif method == "intersection":
        if (left_gdf_type == "Polygon") and (right_gdf_type == "Polygon"):
            gdf = sjoin_largest_area(left_gdf, right_gdf)
        elif (left_gdf_type == "Point") and (right_gdf_type == "Polygon"):
            gdf = intersect_points_polygons(left_gdf, right_gdf, attribute_name)
        else:
            raise NotImplementedError(
                f"Join method {method} is not implemented for joining data of geometry "
                f"type {left_gdf_type} and {right_gdf_type}"
            )
    else:
        raise NotImplementedError(f"Join method {method} is not implemented")

    return gdf


def ground_elevation_from_dem(
    ground_elevation: Union[None, str, Path],
    exposure_db: pd.DataFrame,
    exposure_geoms: gpd.GeoDataFrame,
) -> None:
    # This function was developed by Willem https://github.com/interTwin-eu/DT-flood/blob/DemonstrationNotebooks/Notebooks/SetupFIAT.ipynb
    # TODO: Find equivalent functions in hydromt
    # Read in the DEM
    dem = rasterio.open(ground_elevation)
    # gdf = self.get_full_gdf(exposure_db)

    # TODO if exposure.geoms is not POINTS: either take average value of pixels or create a centroid

    gdf = exposure_geoms.to_crs(dem.crs.data)
    # Create a list of geometries plus a label for rasterize
    # The labels start at 1 since the label 0 is reserved for everything not in a geometry
    # The order of each tuple is (geometry,label)
    shapes = list(enumerate(gdf["geometry"].values))
    shapes = [(t[1], t[0] + 1) for t in shapes]

    rasterized = rasterize(
        shapes=shapes, out_shape=dem.shape, transform=dem.transform, all_touched=True
    )
    # zonal_stats needs xarrays as input
    rasterized = xr.DataArray(rasterized)

    # Calculate the zonal statistics
    zonal_out = zonal_stats(
        rasterized,
        xr.DataArray(dem.read(1)),
        stats_funcs=["mean"],
        nodata_values=np.nan,
    )

    # The zero label is for pixels not in a geometry so we discard them
    zonal_out = zonal_out.drop(0)

    # Array storing the zonal means
    # Store the calculated means at index corresponding to their label
    zonal_means = np.full(len(shapes), np.nan)
    zonal_means[[zonal_out["zone"].values - 1]] = zonal_out["mean"].values

    # Fill nan values with neighboring values. 
    # # Add ground_elevtn column and get rid of nans in the appropriate way
    exposure_db["ground_elevtn"] = zonal_means
    exposure_db["ground_elevtn"].bfill(inplace=True)

    return exposure_db["ground_elevtn"]


def do_geocode(geolocator, xycoords, attempt=1, max_attempts=5):
    try:
        return geolocator.reverse(xycoords)
    except GeocoderTimedOut:
        if attempt <= max_attempts:
            time.sleep(1)
            return do_geocode(geolocator, xycoords, attempt=attempt + 1)
        raise
    except GeocoderUnavailable:
        if attempt <= max_attempts:
            time.sleep(1)
            return do_geocode(geolocator, xycoords, attempt=attempt + 1)
        raise


def locate_from_exposure(buildings):
    geolocator = Nominatim(user_agent="hydromt-fiat")

    # Filter buildings to reduce size
    num_buildings = len(buildings.geometry)
    if num_buildings > 100000:
        buildings_filtered = buildings.geometry[::10000]
    elif num_buildings > 10000:
        buildings_filtered = buildings.geometry[::1000]
    elif num_buildings > 1000:
        buildings_filtered = buildings.geometry[::100]
    elif num_buildings > 100:
        buildings_filtered = buildings.geometry[::10]
    else:
        buildings_filtered = buildings.geometry

    # Find all counties that exposure overlays
    search = []
    for coords in buildings_filtered:
        coordinates = tuple(reversed(coords.coords[0]))
        search.append(coordinates)

    # Find the county and state of the exposure points
    locations = [do_geocode(geolocator, s) for s in search]
    locations_list = [location[0].split(", ") for location in locations]
    locations_list_no_numbers = [
        [y for y in x if not y.isnumeric()] for x in locations_list
    ]

    # TODO: Read from the CSV the counties and check whether the name of the county is in the outcome
    # of the geolocator
    counties = [
        y
        for x in locations_list
        for y in x
        if ("county" in y.lower()) or ("parish" in y.lower())
    ]
    states = [x[-2] for x in locations_list_no_numbers]

    counties_states_combo = set(list(zip(counties, states)))
    counties = [c[0] for c in counties_states_combo]
    states = [c[1] for c in counties_states_combo]

    return counties, states
