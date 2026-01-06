import logging

import geopandas as gpd
import pandas as pd
import pytest

from hydromt_fiat.utils import DAMAGE, MAX
from hydromt_fiat.workflows import max_monetary_damage
from tests.conftest import HAS_INTERNET, HAS_LOCAL_DATA

pytestmark = pytest.mark.skipif(
    not HAS_INTERNET and not HAS_LOCAL_DATA,
    reason="No internet or local data available"
)

def test_max_monetary_damage(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Assert that maximum damage is not already in the dataset
    assert f"{MAX}_{DAMAGE}_structure" not in exposure_vector_clipped_for_damamge

    # Alterations should be inplace, i.e. id before == id after
    id_before = id(exposure_vector_clipped_for_damamge)

    # Call the function
    exposure_vector = max_monetary_damage(
        exposure_data=exposure_vector_clipped_for_damamge,
        exposure_cost_table=exposure_cost_table,
        exposure_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
        country="World",  # Select kwargs
    )
    id_after = id(exposure_vector)

    # Assert that is was inplace
    assert id_before == id_after

    # Assert the content
    assert f"{MAX}_{DAMAGE}_structure" in exposure_vector_clipped_for_damamge
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 663194


def test_max_monetary_damage_link(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
    exposure_cost_link: pd.DataFrame,
):
    # Call the function
    exposure_vector = max_monetary_damage(
        exposure_data=exposure_vector_clipped_for_damamge,
        exposure_cost_table=exposure_cost_table,
        exposure_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
        exposure_cost_link=exposure_cost_link,
        country="World",  # Select kwargs
    )

    # Assert the content
    assert len(exposure_vector) == 12
    assert f"{MAX}_{DAMAGE}_structure" in exposure_vector_clipped_for_damamge
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 663194


def test_max_monetary_damage_link_partial(
    caplog: pytest.LogCaptureFixture,
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
    exposure_cost_link: pd.DataFrame,
):
    caplog.set_level(logging.WARNING)
    # Remove a row from the linking table
    exposure_cost_link.drop(2, inplace=True)  # 2 is industrial
    # Call the function
    exposure_vector = max_monetary_damage(
        exposure_data=exposure_vector_clipped_for_damamge,
        exposure_cost_table=exposure_cost_table,
        exposure_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
        exposure_cost_link=exposure_cost_link,
        country="World",  # Select kwargs
    )

    # Assert the logging
    assert "4 features could not be linked to" in caplog.text

    # Assert the content
    assert len(exposure_vector) == 8
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 822446


def test_max_monetary_damage_geo_crs(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Call the function
    exposure_vector = max_monetary_damage(
        exposure_data=exposure_vector_clipped_for_damamge.to_crs(4326),
        exposure_cost_table=exposure_cost_table,
        exposure_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
        country="World",  # Select kwargs
    )

    # Assert the content
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 662887


def test_max_monetary_damage_no_subtype(
    exposure_geom_data_alt: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers_alt: pd.DataFrame,
):
    # Assert that maximum damage is not already in the dataset
    assert f"{MAX}_{DAMAGE}" not in exposure_geom_data_alt

    # Alterations should be inplace, i.e. id before == id after
    id_before = id(exposure_geom_data_alt)

    # Call the function
    exposure_vector = max_monetary_damage(
        exposure_data=exposure_geom_data_alt,
        exposure_cost_table=exposure_cost_table,
        exposure_type=DAMAGE,
        vulnerability=vulnerability_identifiers_alt,
        country="World",  # Select kwargs
    )
    id_after = id(exposure_vector)

    # Assert that is was inplace
    assert id_before == id_after

    # Assert the content
    assert f"{MAX}_{DAMAGE}" in exposure_geom_data_alt
    assert int(exposure_vector[f"{MAX}_{DAMAGE}"].mean()) == 1363905


def test_max_monetary_damage_errors(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Supply none for the cost table
    with pytest.raises(
        ValueError,
        match="Exposure costs table cannot be None",
    ):
        _ = max_monetary_damage(
            exposure_data=exposure_vector_clipped_for_damamge,
            exposure_cost_table=None,
            exposure_type=DAMAGE,
            vulnerability=vulnerability_identifiers,
        )

    # Select kwargs leave no data
    with pytest.raises(
        ValueError,
        match=r"Select kwargs \(\{'country': 'Unknown'\}\) resulted in no remaining",
    ):
        _ = max_monetary_damage(
            exposure_data=exposure_vector_clipped_for_damamge,
            exposure_cost_table=exposure_cost_table,
            exposure_type=DAMAGE,
            vulnerability=vulnerability_identifiers,
            country="Unknown",
        )

    # Select kwargs leave no data
    with pytest.raises(
        ValueError,
        match=r"Exposure type \(affected\) not found in vulnerability data",
    ):
        _ = max_monetary_damage(
            exposure_data=exposure_vector_clipped_for_damamge,
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
            exposure_data=exposure_vector_clipped_for_damamge,
            exposure_cost_table=exposure_cost_table,
            exposure_type=DAMAGE,
            vulnerability=vulnerability_identifiers,
            country="World",
            exposure_cost_link=pd.DataFrame(),
        )
