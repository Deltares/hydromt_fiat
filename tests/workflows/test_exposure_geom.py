import re

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from hydromt_fiat.utils import CURVE__ID, DAMAGE, FN, OBJECT__ID, OBJECT__TYPE
from hydromt_fiat.workflows import (
    exposure_geoms_add_columns,
    exposure_geoms_link_vulnerability,
    exposure_geoms_setup,
)


def test_exposure_geoms_setup(
    buildings_data: gpd.GeoDataFrame,
    buildings_link_table: pd.DataFrame,
):
    # Simply call the function
    exposure_vector = exposure_geoms_setup(
        exposure_data=buildings_data,
        exposure_object_type_column="gebruiksdoel",
        exposure_link=buildings_link_table,
    )

    # Assert the output
    assert len(exposure_vector) == 9
    assert OBJECT__TYPE in exposure_vector.columns
    assert "industrial" in exposure_vector.object_type.values


def test_exposure_geoms_setup_fill_nodata(
    caplog: pytest.LogCaptureFixture,
    buildings_data: gpd.GeoDataFrame,
    buildings_link_table: pd.DataFrame,
):
    # Produce the warning by default
    exposure_vector = exposure_geoms_setup(
        exposure_data=buildings_data,
        exposure_object_type_column="gebruiksdoel",
        exposure_link=buildings_link_table,
    )

    # Assert the output
    assert "3 features could not be internally linked" in caplog.text
    # The warning should also name the unmapped column and include a
    # breakdown line with a count (form: "<value>: <count>").
    assert "Unmapped values in 'gebruiksdoel'" in caplog.text
    assert ": 3" in caplog.text
    assert len(exposure_vector) == 9

    # Fill the nodata in the linking with a known (irony) value
    exposure_vector = exposure_geoms_setup(
        exposure_data=buildings_data,
        exposure_object_type_column="gebruiksdoel",
        exposure_link=buildings_link_table,
        exposure_object_type_fill="unknown",
    )

    # Assert the output
    assert len(exposure_vector) == 12


def test_exposure_geoms_setup_no_table(
    caplog: pytest.LogCaptureFixture,
    buildings_data: gpd.GeoDataFrame,
):
    # Calling the workflow function without an exposure link table
    exposure_vector = exposure_geoms_setup(
        exposure_data=buildings_data,
        exposure_object_type_column="gebruiksdoel",
    )

    # This will produce a warning
    assert (
        "No exposure link table provided, \
defaulting to exposure data object type"
        in caplog.text
    )
    # Assert that the link names are no in the 'object_type' column
    assert "industrial" not in exposure_vector.object_type.values


def test_exposure_geoms_setup_errors(
    buildings_data: gpd.GeoDataFrame,
    buildings_link_table: pd.DataFrame,
):
    # Supply a exposure type column that is not in the raw exposure data
    with pytest.raises(
        KeyError,
        match="unknown_col not found in the exposure data",
    ):
        _ = exposure_geoms_setup(
            exposure_data=buildings_data,
            exposure_object_type_column="unknown_col",
        )

    # The exposure type column is not found in the link table
    # Pop the correct column
    buildings_link_table.drop("gebruiksdoel", axis=1, inplace=True)

    # Call the methods to produce the error
    with pytest.raises(
        KeyError,
        match="gebruiksdoel not found in the provided linking data",
    ):
        _ = exposure_geoms_setup(
            exposure_data=buildings_data,
            exposure_object_type_column="gebruiksdoel",
            exposure_link=buildings_link_table,
        )


def test_exposure_geoms_link_vulnerability(
    exposure_vector_data_link: gpd.GeoDataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Assert amount of columns in the exposure data
    assert len(exposure_vector_data_link.columns) == 11
    # Assert that these columns are absent
    assert OBJECT__ID not in exposure_vector_data_link.columns
    assert f"{FN}_{DAMAGE}_structure" not in exposure_vector_data_link.columns

    # Call the workflow function
    exposure_vector = exposure_geoms_link_vulnerability(
        exposure_data=exposure_vector_data_link,
        vulnerability=vulnerability_identifiers,
        impact_type=["damage"],
    )

    # Assert the output
    assert len(exposure_vector.columns) == 14
    assert OBJECT__ID in exposure_vector.columns
    assert f"{FN}_{DAMAGE}_structure" in exposure_vector.columns

    # A simple that the curves set in the exposure data (linking) are present
    # in the vulnerability identifiers
    for value in exposure_vector[f"{FN}_{DAMAGE}_structure"].unique():
        assert value in vulnerability_identifiers[CURVE__ID].values


def test_exposure_geoms_link_vulnerability_subtype(
    exposure_vector_data_link: gpd.GeoDataFrame,
    vulnerability_identifiers_alt: pd.DataFrame,
):
    # Assert amount of columns in the exposure data
    assert len(exposure_vector_data_link.columns) == 11
    # Assert that these columns are absent
    assert OBJECT__ID not in exposure_vector_data_link.columns
    assert f"{FN}_{DAMAGE}" not in exposure_vector_data_link.columns

    # Calling the workflow function wihtout subtyping
    exposure_vector = exposure_geoms_link_vulnerability(
        exposure_data=exposure_vector_data_link,
        vulnerability=vulnerability_identifiers_alt,
        impact_type=["damage"],
    )

    # Assert the output
    assert len(exposure_vector.columns) == 13  # One column less
    assert OBJECT__ID in exposure_vector.columns
    assert f"{FN}_{DAMAGE}" in exposure_vector.columns  # Not fn_damage_*, but just base


def test_exposure_geoms_link_vulnerability_warnings(
    caplog: pytest.LogCaptureFixture,
    exposure_vector_data_link: gpd.GeoDataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Fill the nodata in the linking with an unknown (more irony) value
    exposure_vector = exposure_geoms_link_vulnerability(
        exposure_data=exposure_vector_data_link.replace("unknown", "known"),
        vulnerability=vulnerability_identifiers,
        impact_type=["damage"],
    )

    # Assert the output
    assert "3 features could not be linked to vulnerability data" in caplog.text
    assert len(exposure_vector) == 9


def test_exposure_geoms_link_vulnerability_errors(
    exposure_vector_data_link: gpd.GeoDataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Select nonsense impact types
    with pytest.raises(
        ValueError,
        match=re.escape(
            "No data found in the vulnerability identifiers for these \
impact types ['foo', 'bar']"
        ),
    ):
        exposure_geoms_link_vulnerability(
            exposure_data=exposure_vector_data_link,
            vulnerability=vulnerability_identifiers,
            impact_type=["foo", "bar"],
        )


def test_exposure_geoms_add_columns(
    buildings_data: gpd.GeoDataFrame,
):
    # Assert that the columns are not there
    assert "col1" not in buildings_data
    assert "col2" not in buildings_data
    # Should be in situ, so same id before == id after
    id_before = id(buildings_data)

    # Call the workflow function
    exposure_vector = exposure_geoms_add_columns(
        buildings_data,
        columns=["col1", "col2"],
        values=10,
    )
    id_after = id(exposure_vector)

    # Assert that the operations were indeed inplace
    assert id_before == id_after

    # Assert the columns were created
    assert "col1" in exposure_vector
    assert "col2" in exposure_vector

    # Assert that mean value is indeed 10
    assert exposure_vector["col1"].mean() == 10


def test_exposure_geoms_add_columns_list(
    buildings_data: gpd.GeoDataFrame,
):
    # Call the workflow function
    exposure_vector = exposure_geoms_add_columns(
        buildings_data,
        columns=["col1", "col2"],
        values=[10, 20],
    )

    # Assert the different values
    assert exposure_vector["col1"].mean() == 10
    assert exposure_vector["col2"].mean() == 20


def test_exposure_geoms_add_columns_array(
    buildings_data: gpd.GeoDataFrame,
):
    # Create the data
    data = np.column_stack(
        (
            np.arange(0, 12, 1),
            np.arange(10, 22, 1),
        ),
    )
    # Call the workflow function
    exposure_vector = exposure_geoms_add_columns(
        buildings_data,
        columns=["col1", "col2"],
        values=data,
    )

    # Assert the different values
    assert int(exposure_vector["col1"].mean() * 10) == 55
    assert int(exposure_vector["col2"].mean() * 10) == 155


def test_exposure_geoms_add_columns_errors(
    buildings_data: gpd.GeoDataFrame,
):
    # Create the data
    data = np.column_stack(
        (
            np.arange(0, 12, 1),
            np.arange(10, 22, 1),
            np.arange(20, 32, 1),
        ),
    )
    # Give the wrong array in terms of shape as input
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Length of the columns (2) is not the same as the length of the values (3)."
        ),
    ):
        _ = exposure_geoms_add_columns(
            buildings_data,
            columns=["col1", "col2"],
            values=data,
        )
