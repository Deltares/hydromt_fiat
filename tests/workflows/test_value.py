import logging
import re

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import shapely.geometry as sg

from hydromt_fiat.utils import COST__TYPE, DAMAGE, MAX
from hydromt_fiat.workflows import max_value, max_value_direct, process_cost_table
from hydromt_fiat.workflows.value import get_geometry_type, spatial_dimensions


def test_get_geometry_type():
    # Call the function
    out = get_geometry_type(gpd.GeoDataFrame(geometry=[sg.Point(1, 1)]))
    # Assert the output
    assert out == 0

    # Call the function
    out = get_geometry_type(
        gpd.GeoDataFrame(geometry=[sg.LineString(((1, 1), (2, 2)))])
    )
    # Assert the output
    assert out == 1

    # Call the function
    out = get_geometry_type(gpd.GeoDataFrame(geometry=[sg.box(0, 0, 1, 1)]))
    # Assert the output
    assert out == 2


def test_get_geometry_type_errors():
    # Call the function with a non-supported geometry type
    with pytest.raises(
        ValueError, match="Unsupported geometry types: {'GeometryCollection'}"
    ):
        _ = get_geometry_type(
            gdf=gpd.GeoDataFrame(
                geometry=[
                    sg.GeometryCollection([sg.box(0, 0, 1, 1), sg.box(2, 2, 3, 3)])
                ]
            )
        )


def test_spatial_dimensions():
    # Call the function
    out = spatial_dimensions(
        exposure_data=gpd.GeoDataFrame(geometry=[sg.box(0, 0, 1, 1)]),
    )
    # Assert the output
    np.testing.assert_array_almost_equal(actual=out, desired=[1], decimal=0)

    # Call the function
    out = spatial_dimensions(
        exposure_data=gpd.GeoDataFrame(geometry=[sg.LineString(((1, 1), (2, 2)))]),
    )
    # Assert the output
    np.testing.assert_array_almost_equal(actual=out, desired=[1.41], decimal=2)


def test_spatial_dimensions_crs():
    # Call the function
    g = gpd.GeoDataFrame(geometry=[sg.box(0, 0, 1, 1)], crs=4326)
    out = spatial_dimensions(exposure_data=g)
    # Assert the output
    assert g.crs.to_epsg() == 32631
    np.testing.assert_array_almost_equal(
        actual=out,
        desired=[12322539176],
        decimal=0,
    )


def test_spatial_dimensions_erros():
    # Call the function with point geometry
    with pytest.raises(
        ValueError, match="Point geometries do not have a spatial dimension"
    ):
        _ = spatial_dimensions(
            exposure_data=gpd.GeoDataFrame(geometry=[sg.Point(1, 1)])
        )


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


def test_max_value_direct(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
):
    # Call the function
    e = max_value_direct(
        exposure_data=exposure_vector_clipped_for_damamge,
        value=100,
        impact_type="damage",
        per_unit=False,
    )
    # Assert the output
    assert "max_damage" in e.columns
    np.testing.assert_almost_equal(e["max_damage"].mean(), 100, decimal=0)

    # Call the function with subtype
    e = max_value_direct(
        exposure_data=exposure_vector_clipped_for_damamge,
        value=50,
        impact_type="damage",
        impact_subtype="content",
        per_unit=False,
    )
    # Assert the output
    assert "max_damage_content" in e.columns
    np.testing.assert_almost_equal(e["max_damage_content"].mean(), 50, decimal=0)


def test_max_value_direct_unit(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
):
    # Call the function
    e = max_value_direct(
        exposure_data=exposure_vector_clipped_for_damamge,
        value=100,
        impact_type="damage",
        per_unit=True,
    )
    # Assert the output
    np.testing.assert_almost_equal(e["max_damage"].mean(), 222427, decimal=0)
