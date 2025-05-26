import geopandas as gpd
import pandas as pd
import pytest

from hydromt_fiat.workflows import max_monetary_damage


def test_max_monetary_damage(
    exposure_geom_data_reduced: gpd.GeoDataFrame,
    exposure_geom_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Assert that maximum damage is not already in the dataset
    assert "max_damage_structure" not in exposure_geom_data_reduced

    # Alterations should be inplace, i.e. id before == id after
    id_before = id(exposure_geom_data_reduced)

    # Call the function
    exposure_vector = max_monetary_damage(
        exposure_data=exposure_geom_data_reduced,
        exposure_cost_table=exposure_geom_cost_table,
        exposure_type="damage",
        vulnerability=vulnerability_identifiers,
        country="World",  # Select kwargs
    )
    id_after = id(exposure_vector)

    # Assert that is was inplace
    assert id_before == id_after

    # Assert the content
    assert "max_damage_structure" in exposure_geom_data_reduced
    assert int(exposure_vector["max_damage_structure"].mean()) == 371274


def test_max_monetary_damage_errors(
    exposure_geom_data_reduced: gpd.GeoDataFrame,
    exposure_geom_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Supply none for the cost table
    with pytest.raises(
        ValueError,
        match="Exposure costs table cannot be None",
    ):
        _ = max_monetary_damage(
            exposure_data=exposure_geom_data_reduced,
            exposure_cost_table=None,
            exposure_type="damage",
            vulnerability=vulnerability_identifiers,
        )

    # Select kwargs leave no data
    with pytest.raises(
        ValueError,
        match=r"Select kwargs \(\{'country': 'Unknown'\}\) resulted in no remaining",
    ):
        _ = max_monetary_damage(
            exposure_data=exposure_geom_data_reduced,
            exposure_cost_table=exposure_geom_cost_table,
            exposure_type="damage",
            vulnerability=vulnerability_identifiers,
            country="Unknown",
        )
