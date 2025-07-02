import logging
import time
from typing import List, Literal

import geopandas as gpd
import numpy as np
import pandas as pd
import pint
import xarray as xr
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
from hydromt.gis_utils import nearest_merge, utm_crs
from xrspatial import zonal_stats

from hydromt_fiat.api.data_types import Conversion


def get_area(gdf: gpd.GeoDataFrame, model_length_unit: str) -> gpd.GeoDataFrame:
    """Adds an area column to a GeoDataFrame.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        The GeoDataFrame to which the area column will be added.
    model_length_unit: 
        The length unit of the model in meters or feet. 

    Returns
    -------
    gpd.GeoDataFrame
        The GeoDataFrame with an additional column "area".
    """
    # Calculate the area of each object
    if gdf.crs.is_geographic:
        # If the CRS is geographic, reproject to the nearest UTM zone
        nearest_utm = utm_crs(gdf.total_bounds)
        unit = nearest_utm.axis_info[0].unit_name
        gdf_utm = gdf.to_crs(nearest_utm)
        gdf["area"] = gdf_utm["geometry"].area
    elif gdf.crs.is_projected:
        # If the CRS is projected, calculate the area in the same CRS
        unit = gdf.crs.axis_info[0].unit_name
        gdf["area"] = gdf["geometry"].area
    
    ureg = pint.UnitRegistry()
    unit = ureg(unit).units
    model_unit = ureg(model_length_unit).units
    
    
    if unit != model_unit:
        if model_unit == ureg("meters").units and unit == ureg("feets").units:
            gdf["area"] = gdf["area"] * (Conversion.feet_to_meters.value)**2
        elif model_unit == ureg("feets").units and unit == ureg("meters").units:
            gdf["area"] = gdf["area"] * (Conversion.meters_to_feet.value)**2
        else:
            raise ValueError(f"Unsupported unit: {unit}")
    
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
    if "MultiPolygon" in list(gdf.geom_type.unique()):
        for index, row in gdf.iterrows():
            if row["geometry"].geom_type == "MultiPolygon":
                largest_polygon = max(row["geometry"].geoms, key=lambda a: a.area)
                gdf.at[index, "geometry"] = largest_polygon
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
    dem_da: xr.DataArray,
    exposure_geoms: gpd.GeoDataFrame,
    stats_func: Literal["mean", "min"] = "mean",
    logger: logging.Logger = None
) -> pd.Series:
    """Calculate the ground elevation from a DEM for the given exposure geometries.

    Parameters
    ----------
    dem_da : xr.DataArray
        The DEM data as an xarray DataArray.
    exposure_geoms : gpd.GeoDataFrame
        The exposure geometries as a GeoDataFrame.
    stats_func : Literal["mean", "min"], optional
        The statistic to calculate for the ground elevation, by default "mean".
    
    Returns
    -------
    pd.Series
        A pandas Series containing the ground elevation for each exposure geometry.
    """
    # rasterize the exposure geometries to match the DEM raster
    # NOTE that multiple buildings can fall into the same pixel, which we deal with later
    gdf = exposure_geoms.reset_index(drop=True).to_crs(dem_da.raster.crs).copy()
    gdf.index = gdf.index.astype(int) + 1  # Ensure index starts at 1 for rasterization
    da_exposure_id = dem_da.raster.rasterize(gdf, all_touched=True, nodata=0)

    # Calculate the zonal statistics using xrspatial
    # NOTE this is much faster than using hydromt.raster.zonal_stats, but we need to 
    # deal with the fact that multiple buildings can fall into the same pixel
    df_elev = zonal_stats(
        da_exposure_id,
        dem_da.load(),
        stats_funcs=[stats_func],
        nodata_values=np.nan,
    ).set_index("zone")["mean"]

    # Reindex to match the exposure GeoDataFrame
    # and set the ground_elevtn column
    gdf["ground_elevtn"] = df_elev.reindex(
        gdf.index, fill_value=np.nan
    )  

    # fill nan values for buildings that fall into the same pixel
    nan_geoms = gdf[gdf["ground_elevtn"].isna()]
    # use centroid to sample the values from the raster
    if not nan_geoms.empty:
        logger.debug(
            f"Found {len(nan_geoms)} geometries which were not rasterized. "
            "Filling based on geometry centroid."
        )
        sampled_ids = da_exposure_id.raster.sample(
            nan_geoms.geometry.centroid
        )
        gdf.loc[nan_geoms.index, "ground_elevtn"] = gdf.loc[sampled_ids.values, "ground_elevtn"].values

    # fill remaining nan values with its nearest geographical neighbor
    nan_geoms = gdf[gdf["ground_elevtn"].isna()]
    if not nan_geoms.empty:
        logger.warning(
            f"Found {len(nan_geoms)} geometries with no ground elevation data. "
            "Filling with nearest neighbor."
        )
        nearest_ids = gdf.sindex.nearest(nan_geoms.geometry, exclusive=True, return_all=False)
        gdf.loc[nan_geoms.index, "ground_elevtn"] = gdf.loc[nearest_ids, "ground_elevtn"].values

    gdf.index = exposure_geoms.index  # Restore original index
    return gdf["ground_elevtn"]


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
