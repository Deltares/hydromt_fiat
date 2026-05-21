"""Some functions for aggregation."""

import logging
import uuid

import geopandas as gpd
from hydromt.gis import utm_crs

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

    Returns
    -------
    gpd.GeoDataFrame
        The vector grid with aggregated values.
    """
    # Set the data to points (centroids)
    output_data.geometry = output_data.centroid

    column = str(uuid.uuid1())
    aggregation_areas.reset_index(names=[column], inplace=True)
    aggregation_areas = aggregation_areas.loc[:, ["geometry", column]]

    # Overlay with the fiat output
    output_data = output_data.overlay(aggregation_areas, how="intersection")
    output_data = output_data.dissolve(by=column, aggfunc=method)
    output_data.drop("geometry", axis=1, inplace=True)

    # Merge back
    aggregation_areas = aggregation_areas.merge(output_data, on=column, how="left")
    aggregation_areas.drop([column], axis=1, inplace=True)

    # Return the aggregation dataset
    return aggregation_areas
