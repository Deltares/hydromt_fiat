import geopandas as gpd
import numpy as np

from hydromt_fiat.workflows.aggregate import (
    aggregate_spatially,
    prep_data_for_aggregation,
)


def test_prep_data_for_aggregation(
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Assert current state
    assert len(exposure_vector_clipped.columns) == 18
    assert exposure_vector_clipped.crs.to_epsg() == 28992

    # Call the function
    o = prep_data_for_aggregation(output_data=exposure_vector_clipped)

    # Assert the state after
    assert len(o.columns) == 5
    assert o.crs.to_epsg() == 28992  # nothing happened


def test_prep_data_for_aggregation_crs(
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Alter and assert current state
    data = exposure_vector_clipped.to_crs(4326)
    assert data.crs.to_epsg() == 4326

    # Call the function
    o = prep_data_for_aggregation(output_data=data)

    # Assert the state after
    assert o.crs.to_epsg() == 32631  # Reprojected to projected crs


def test_aggregate_spatially(
    prepped_aggr_data: gpd.GeoDataFrame,
    vector_grid: gpd.GeoDataFrame,
):
    # Call the function
    vg = aggregate_spatially(
        output_data=prepped_aggr_data,
        aggregation_areas=vector_grid,
        method="mean",
    )

    # Assert the output
    assert len(vg) == 20
    np.testing.assert_almost_equal(vg["max_damage_content"].iloc[0], 155730, decimal=0)
    np.testing.assert_almost_equal(
        np.nanmean(vg["max_damage_content"]),
        desired=796843,
        decimal=0,
    )


def test_aggregate_spatially_sum(
    prepped_aggr_data: gpd.GeoDataFrame,
    vector_grid: gpd.GeoDataFrame,
):
    # Call the function
    vg = aggregate_spatially(
        output_data=prepped_aggr_data,
        aggregation_areas=vector_grid,
        method="sum",
    )

    # Assert the output
    assert len(vg) == 20
    np.testing.assert_almost_equal(vg["max_damage_content"].iloc[0], 155730, decimal=0)
    np.testing.assert_almost_equal(
        np.nanmean(vg["max_damage_content"]),
        desired=840854,
        decimal=0,
    )


def test_aggregate_spatially_areal_mean(
    prepped_aggr_data: gpd.GeoDataFrame,
    vector_grid: gpd.GeoDataFrame,
):
    # Call the function
    vg = aggregate_spatially(
        output_data=prepped_aggr_data,
        aggregation_areas=vector_grid,
        method="sum",
        areal_mean=True,
    )

    # Assert the output
    assert len(vg) == 20
    np.testing.assert_almost_equal(vg["max_damage_content"].iloc[0], 326, decimal=0)
    np.testing.assert_almost_equal(
        np.nanmean(vg["max_damage_content"]),
        desired=301,
        decimal=0,
    )


def test_aggregate_spatially_areal_mean_per(
    prepped_aggr_data: gpd.GeoDataFrame,
    vector_grid: gpd.GeoDataFrame,
):
    # Call the function
    vg = aggregate_spatially(
        output_data=prepped_aggr_data,
        aggregation_areas=vector_grid,
        method="sum",
        areal_mean=True,
        per_area=True,
    )

    # Assert the output
    assert len(vg) == 20
    np.testing.assert_almost_equal(vg["max_damage_content"].iloc[0], 15.6, decimal=1)
    np.testing.assert_almost_equal(
        np.nanmean(vg["max_damage_content"]),
        desired=84.1,
        decimal=1,
    )
