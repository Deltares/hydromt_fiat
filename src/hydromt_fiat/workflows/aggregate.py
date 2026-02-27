"""Some functions for aggregation."""

import logging
import math

import geopandas as gpd
from hydromt.gis import full_from_transform, utm_crs

__all__ = ["aggregate_vector_grid"]

logger = logging.getLogger(f"hydromt.{__name__}")


def aggregate_vector_grid(
    output_data: gpd.GeoDataFrame,
    res: float | int,
    method: str,
    region: gpd.GeoDataFrame | None = None,
) -> gpd.GeoDataFrame:
    """Aggregate data on a square vector grid.

    Parameters
    ----------
    output_data : gpd.GeoDataFrame
        The output vector data set from FIAT.
    res : float | int
        The resolution of the vector grid.
    method : str
        The method of aggregation.
    region : gpd.GeoDataFrame, optional
        A region to clip the data to.

    Returns
    -------
    gpd.GeoDataFrame
        The vector grid with aggregated values.
    """
    float_data: gpd.GeoDataFrame = output_data.select_dtypes(
        include=[float, "geometry"],
    )

    # Get the crs
    dcrs = float_data.crs
    # Sort out the potential geographic issue
    crs = dcrs
    if dcrs and dcrs.is_geographic:
        logger.warning("CRS of data was geographic, reprojecting to projected crs")
        crs = utm_crs(float_data.total_bounds)
        float_data.to_crs(crs, inplace=True)

    # Km to meters
    res = res * 1000

    # Get some properties from the data
    bbox = float_data.total_bounds
    dx = bbox[2] - bbox[0]
    dy = bbox[3] - bbox[1]

    # Set the data to points (centroids)
    float_data.geometry = float_data.centroid

    # Create a grid based on the bounding box of the results
    # and the resolution for the input
    vg: gpd.GeoDataFrame = full_from_transform(
        transform=(res, 0.0, bbox[0], 0.0, -res, bbox[3]),
        shape=(math.ceil(dy / res), math.ceil(dx / res)),
        crs=float_data.crs,
    ).raster.vector_grid()
    vg["square_id"] = range(len(vg))

    # Overlay with the fiat output
    float_data = float_data.overlay(vg, how="intersection")
    float_data = float_data.dissolve(by="square_id", aggfunc=method)
    float_data.drop("geometry", axis=1, inplace=True)

    # Merge back
    vg = vg.merge(float_data, on="square_id", how="left")
    # If there is a region, clip the resulting vector grid
    if region is not None:
        logger.info("Clipping the results based on the provided region")
        vg = vg[vg["square_id"].isin(vg.overlay(region.to_crs(vg.crs))["square_id"])]

    return vg
