import geopandas as gpd
import numpy as np

from hydromt_fiat.workflows.aggregate import aggregate_vector_grid


def test_aggregate_vector_grid(
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Call the function
    vg = aggregate_vector_grid(
        output_data=exposure_vector_clipped,
        res=0.1,
        method="mean",
    )

    # Assert the output
    assert len(vg) == 20
    np.testing.assert_almost_equal(vg["max_damage_content"].iloc[0], 155730, decimal=0)


def test_aggregate_vector_grid_crs(
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Reproject
    data = exposure_vector_clipped.to_crs(4326)
    assert data.crs.to_epsg() == 4326
    # Call the function
    vg = aggregate_vector_grid(
        output_data=data,
        res=0.1,
        method="mean",
    )

    # Assert the output
    assert vg.crs.to_epsg() == 32631
    assert len(vg) == 20
    np.testing.assert_almost_equal(vg["max_damage_content"].iloc[0], 155730, decimal=0)


def test_aggregate_vector_grid_region(
    exposure_vector_clipped: gpd.GeoDataFrame,
    build_region_small: gpd.GeoDataFrame,
):
    # Call the function
    vg = aggregate_vector_grid(
        output_data=exposure_vector_clipped,
        res=0.1,
        method="mean",
        region=build_region_small,
    )

    # Assert the output
    assert len(vg) == 18
    np.testing.assert_almost_equal(vg["max_damage_content"].iloc[0], 155730, decimal=0)
