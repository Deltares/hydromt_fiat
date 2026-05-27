"""Some functions for aggregation."""

import logging
import uuid

import geopandas as gpd
from hydromt.gis import utm_crs

from hydromt_fiat.utils import AREA__SQM, GEOMETRY

__all__ = [
    "aggregate_spatially",
    "prep_data_for_aggregation",
]

logger = logging.getLogger(f"hydromt.{__name__}")


def prep_data_for_aggregation(
    output_data: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Prepare the output data for aggregation.

    Ensures projected crs and only floating point data.

    Parameters
    ----------
    output_data : gpd.GeoDataFrame
        The FIAT model output data.

    Returns
    -------
    gpd.GeoDataFrame
        The dataset ready for aggregation.
    """
    # Select only the floating point data.
    partial_data: gpd.GeoDataFrame = output_data.select_dtypes(
        include=[float, "geometry"],
    )

    # Get the crs
    dcrs = partial_data.crs
    # Sort out the potential geographic issue
    if dcrs and dcrs.is_geographic:
        logger.warning("CRS of data was geographic, reprojecting to projected crs")
        crs = utm_crs(partial_data.total_bounds)
        partial_data.to_crs(crs, inplace=True)

    # Return the dataset
    return partial_data


def aggregate_spatially(
    output_data: gpd.GeoDataFrame,
    aggregation_areas: gpd.GeoDataFrame,
    method: str,
    areal_mean: bool = False,
    per_area: bool = False,
) -> gpd.GeoDataFrame:
    """Aggregate data on a square vector grid.

    Warning
    -------
    Run :py:func:`~prep_data_for_aggregation` beforehand.

    Parameters
    ----------
    output_data : gpd.GeoDataFrame
        The output vector data set from FIAT, made ready for aggregation.
    aggregation_areas : gpd.GeoDataFrame
        The dataset with areas over which to aggregate the data.
    method : str
        The method of aggregation.
    areal_mean : bool, optional
        Whether or not to calculate the values per unit area (m2). By default False.
    per_area : bool, optional
        Whether or not to calculate per unit area using the aggregation area (True) or
        the combined (based on method) area of the features in the `output_data`.
        By default False.

    Returns
    -------
    gpd.GeoDataFrame
        The vector grid with aggregated values.
    """
    logger.info("Aggregating spatially..")
    # Set the data to points (centroids)
    output_data[AREA__SQM] = output_data.area
    output_data.geometry = output_data.centroid

    column = str(uuid.uuid1())
    aggregation_areas = aggregation_areas.reset_index(names=[column])
    aggregation_areas = aggregation_areas.loc[:, [GEOMETRY, column]]

    # Overlay with the fiat output
    output_data = output_data.overlay(aggregation_areas, how="intersection")
    output_data = output_data.dissolve(by=column, aggfunc=method)
    output_data.drop(GEOMETRY, axis=1, inplace=True)

    # Merge back
    aggregation_areas = aggregation_areas.merge(output_data, on=column, how="left")
    aggregation_areas.drop([column], axis=1, inplace=True)

    # Check if one wants a areal mean (spatial average), if not return directly
    if not areal_mean:
        return aggregation_areas

    logger.info(f"Spatially averaging the data with 'per_area' set to: {per_area}")
    # Check if it is wanted per object area or aggregation area
    if per_area or sum(aggregation_areas[AREA__SQM]) == 0:
        aggregation_areas[AREA__SQM] = aggregation_areas.area

    # Do it only over the numeric columns
    float_cols = aggregation_areas.columns.drop([GEOMETRY, AREA__SQM])
    aggregation_areas[float_cols] = aggregation_areas[float_cols].div(
        aggregation_areas[AREA__SQM],
        axis=0,
    )

    # Return the aggregation dataset
    return aggregation_areas
