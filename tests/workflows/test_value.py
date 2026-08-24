import logging
import re

import geopandas as gpd
import pandas as pd
import pytest

from hydromt_fiat.utils import COST__TYPE, DAMAGE, MAX
from hydromt_fiat.workflows import max_value, process_cost_table


def test_process_cost_table(
    exposure_cost_table: pd.DataFrame,
):
    # Call the function
    cost_table = process_cost_table(
        exposure_cost_table=exposure_cost_table,
        **{"country": "World"},
    )

    # Assert the content
    assert isinstance(cost_table, pd.DataFrame)
    assert len(cost_table) == 14
    assert "commercial" in cost_table[COST__TYPE].values
    assert "commercial_structure" in cost_table[COST__TYPE].values


def test_process_cost_table_dict(exposure_cost_dict: dict[str, float]):
    # Call the function
    cost_table = process_cost_table(exposure_cost_table=exposure_cost_dict)

    # Assert the content
    assert isinstance(cost_table, pd.DataFrame)
    assert len(cost_table) == 8
    assert "commercial_structure" in cost_table[COST__TYPE].values


def test_process_cost_table_errors(
    exposure_cost_table: pd.DataFrame,
):
    # Select kwargs leave no data
    with pytest.raises(
        ValueError,
        match=r"Select kwargs \(\{'country': 'Foo'\}\) resulted in no remaining",
    ):
        _ = process_cost_table(
            exposure_cost_table=exposure_cost_table,
            country="Foo",
        )


def test_max_value(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table_processed: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Assert that maximum damage is not already in the dataset
    assert f"{MAX}_{DAMAGE}_structure" not in exposure_vector_clipped_for_damamge

    # Alterations should be inplace, i.e. id before == id after
    id_before = id(exposure_vector_clipped_for_damamge)

    # Call the function
    exposure_vector = max_value(
        exposure_data=exposure_vector_clipped_for_damamge,
        exposure_cost_table=exposure_cost_table_processed,
        impact_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
    )
    id_after = id(exposure_vector)

    # Assert that is was inplace
    assert id_before == id_after

    # Assert the content
    assert f"{MAX}_{DAMAGE}_structure" in exposure_vector_clipped_for_damamge
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 663194


def test_max_value_link(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table_processed: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
    exposure_cost_link: pd.DataFrame,
):
    # Call the function
    exposure_vector = max_value(
        exposure_data=exposure_vector_clipped_for_damamge,
        exposure_cost_table=exposure_cost_table_processed,
        impact_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
        exposure_cost_link=exposure_cost_link,
    )

    # Assert the content
    assert len(exposure_vector) == 12
    assert f"{MAX}_{DAMAGE}_structure" in exposure_vector_clipped_for_damamge
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 663194


def test_max_value_link_partial(
    caplog: pytest.LogCaptureFixture,
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table_processed: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
    exposure_cost_link: pd.DataFrame,
):
    caplog.set_level(logging.WARNING)
    # Remove a row from the linking table
    exposure_cost_link.drop(2, inplace=True)  # 2 is industrial
    # Call the function
    exposure_vector = max_value(
        exposure_data=exposure_vector_clipped_for_damamge,
        exposure_cost_table=exposure_cost_table_processed,
        impact_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
        exposure_cost_link=exposure_cost_link,
    )

    # Assert the logging
    assert "4 features could not be linked to" in caplog.text

    # Assert the content
    assert len(exposure_vector) == 8
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 822446


def test_max_value_geo_crs(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table_processed: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Call the function
    exposure_vector = max_value(
        exposure_data=exposure_vector_clipped_for_damamge.to_crs(4326),
        exposure_cost_table=exposure_cost_table_processed,
        impact_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
    )

    # Assert the content
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 662887


def test_max_value_no_subtype(
    exposure_vector_data_alt: gpd.GeoDataFrame,
    exposure_cost_table_processed: pd.DataFrame,
    vulnerability_identifiers_alt: pd.DataFrame,
):
    # Assert that maximum damage is not already in the dataset
    assert f"{MAX}_{DAMAGE}" not in exposure_vector_data_alt

    # Alterations should be inplace, i.e. id before == id after
    id_before = id(exposure_vector_data_alt)

    # Call the function
    exposure_vector = max_value(
        exposure_data=exposure_vector_data_alt,
        exposure_cost_table=exposure_cost_table_processed,
        impact_type=DAMAGE,
        vulnerability=vulnerability_identifiers_alt,
    )
    id_after = id(exposure_vector)

    # Assert that is was inplace
    assert id_before == id_after

    # Assert the content
    assert f"{MAX}_{DAMAGE}" in exposure_vector_data_alt
    assert int(exposure_vector[f"{MAX}_{DAMAGE}"].mean()) == 1363905


def test_max_value_errors(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table_processed: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Select kwargs leave no data
    with pytest.raises(
        ValueError,
        match=re.escape(
            "No data found in the vulnerability identifiers for \
these impact types ['affected']"
        ),
    ):
        _ = max_value(
            exposure_data=exposure_vector_clipped_for_damamge,
            exposure_cost_table=exposure_cost_table_processed,
            impact_type="affected",
            vulnerability=vulnerability_identifiers,
        )

    # Exposure cost link table missing columns
    with pytest.raises(
        ValueError,
        match="Cost link table either missing object_type or cost_type",
    ):
        _ = max_value(
            exposure_data=exposure_vector_clipped_for_damamge,
            exposure_cost_table=exposure_cost_table_processed,
            impact_type=DAMAGE,
            vulnerability=vulnerability_identifiers,
            exposure_cost_link=pd.DataFrame(),
        )
