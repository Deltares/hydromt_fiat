import geopandas as gpd
import pandas as pd
import pytest

from hydromt_fiat.workflows import max_monetary_damage


def test_max_monetary_damage(
    exposure_geom_data_damage: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Assert that maximum damage is not already in the dataset
    assert "max_damage_structure" not in exposure_geom_data_damage

    # Alterations should be inplace, i.e. id before == id after
    id_before = id(exposure_geom_data_damage)

    # Call the function
    exposure_vector = max_monetary_damage(
        exposure_data=exposure_geom_data_damage,
        exposure_cost_table=exposure_cost_table,
        exposure_type="damage",
        vulnerability=vulnerability_identifiers,
        country="World",  # Select kwargs
    )
    id_after = id(exposure_vector)

    # Assert that is was inplace
    assert id_before == id_after

    # Assert the content
    assert "max_damage_structure" in exposure_geom_data_damage
    assert int(exposure_vector["max_damage_structure"].mean()) == 663194


def test_max_monetary_damage_geo_crs(
    exposure_geom_data_damage: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Call the function
    exposure_vector = max_monetary_damage(
        exposure_data=exposure_geom_data_damage.to_crs(4326),
        exposure_cost_table=exposure_cost_table,
        exposure_type="damage",
        vulnerability=vulnerability_identifiers,
        country="World",  # Select kwargs
    )

    # Assert the content
    assert int(exposure_vector["max_damage_structure"].mean()) == 662887


def test_max_monetary_damage_no_subtype(
    exposure_geom_data_alt: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers_alt: pd.DataFrame,
):
    # Assert that maximum damage is not already in the dataset
    assert "max_damage" not in exposure_geom_data_alt

    # Alterations should be inplace, i.e. id before == id after
    id_before = id(exposure_geom_data_alt)

    # Call the function
    exposure_vector = max_monetary_damage(
        exposure_data=exposure_geom_data_alt,
        exposure_cost_table=exposure_cost_table,
        exposure_type="damage",
        vulnerability=vulnerability_identifiers_alt,
        country="World",  # Select kwargs
    )
    id_after = id(exposure_vector)

    # Assert that is was inplace
    assert id_before == id_after

    # Assert the content
    assert "max_damage" in exposure_geom_data_alt
    assert int(exposure_vector["max_damage"].mean()) == 1363905


def test_max_monetary_damage_errors(
    exposure_geom_data_damage: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Supply none for the cost table
    with pytest.raises(
        ValueError,
        match="Exposure costs table cannot be None",
    ):
        _ = max_monetary_damage(
            exposure_data=exposure_geom_data_damage,
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
            exposure_data=exposure_geom_data_damage,
            exposure_cost_table=exposure_cost_table,
            exposure_type="damage",
            vulnerability=vulnerability_identifiers,
            country="Unknown",
        )

    # Select kwargs leave no data
    with pytest.raises(
        ValueError,
        match=r"Exposure type \(affected\) not found in vulnerability data",
    ):
        _ = max_monetary_damage(
            exposure_data=exposure_geom_data_damage,
            exposure_cost_table=exposure_cost_table,
            exposure_type="affected",
            vulnerability=vulnerability_identifiers,
            country="World",
        )

    # Exposure cost link table missing columns
    with pytest.raises(
        ValueError,
        match="Cost link table either missing object_type or cost_type",
    ):
        _ = max_monetary_damage(
            exposure_data=exposure_geom_data_damage,
            exposure_cost_table=exposure_cost_table,
            exposure_type="damage",
            vulnerability=vulnerability_identifiers,
            country="World",
            exposure_cost_link=pd.DataFrame(),
        )
