import math

import geopandas as gpd
import numpy as np

from hydromt_fiat.gis import create_square_vector_grid
from hydromt_fiat.utils import SQUARE__ID


def test_create_square_vector_grid(
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Call the function
    bbox = exposure_vector_clipped.total_bounds
    vg = create_square_vector_grid(
        bbox=bbox,
        crs=exposure_vector_clipped.crs,
        res=0.1,
        unit="km",
    )

    # Assert the output properties
    assert vg.crs.to_epsg() == exposure_vector_clipped.crs.to_epsg()
    assert (
        len(vg)
        == (math.ceil((bbox[2] - bbox[0]) / 100) * math.ceil((bbox[3] - bbox[1]) / 100))
        == 20
    )
    assert SQUARE__ID in vg.columns
    np.testing.assert_array_equal(vg[SQUARE__ID], range(0, 20))


def test_create_square_vector_grid_unit(
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Call the function
    bbox = exposure_vector_clipped.total_bounds
    vg = create_square_vector_grid(
        bbox=bbox,
        crs=exposure_vector_clipped.crs,
        res=0.1,
        unit="mile",
    )

    # Assert the output properties
    assert (
        len(vg)
        == (
            math.ceil((bbox[2] - bbox[0]) / (100 * 1.6))
            * math.ceil((bbox[3] - bbox[1]) / (100 * 1.6))
        )
        == 9
    )
