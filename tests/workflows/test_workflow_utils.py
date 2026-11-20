import pandas as pd
import pytest
import xarray as xr

from hydromt_fiat.utils import COST__TYPE, VALUE
from hydromt_fiat.workflows import ensure_dataset, process_table


def test_process_table(
    exposure_cost_table: pd.DataFrame,
):
    # Call the function
    cost_table = process_table(
        table=exposure_cost_table,
        column_name=VALUE,
        index_name=COST__TYPE,
        **{"country": "World"},
    )

    # Assert the content
    assert isinstance(cost_table, pd.DataFrame)
    assert len(cost_table) == 14
    assert "commercial" in cost_table[COST__TYPE].values
    assert "commercial_structure" in cost_table[COST__TYPE].values


def test_process_table_dict(exposure_cost_dict: dict[str, float]):
    # Call the function
    cost_table = process_table(
        table=exposure_cost_dict,
        column_name=VALUE,
        index_name=COST__TYPE,
    )

    # Assert the content
    assert isinstance(cost_table, pd.DataFrame)
    assert len(cost_table) == 8
    assert "commercial_structure" in cost_table[COST__TYPE].values


def test_process_table_errors(
    exposure_cost_table: pd.DataFrame,
):
    # Select kwargs leave no data
    with pytest.raises(
        ValueError,
        match=r"Select kwargs \(\{'country': 'Foo'\}\) resulted in no remaining",
    ):
        _ = process_table(
            table=exposure_cost_table,
            column_name=VALUE,
            index_name=COST__TYPE,
            country="Foo",
        )


def test_ensure_dataset(
    vulnerability_curves: xr.Dataset,
):
    # Call the function with a dataset
    ds = ensure_dataset(vulnerability_curves)

    # Assert the output, nothing should have changed
    assert ds is vulnerability_curves


def test_ensure_dataset_data_array(
    vulnerability_curves: xr.Dataset,
):
    # Setup a data array with a name
    da = vulnerability_curves["default"].copy()

    # Call the function
    ds = ensure_dataset(da)

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert list(ds.data_vars) == ["default"]

    # Call the function with a name, which takes precedence
    ds = ensure_dataset(da, name="foo")

    # Assert the output
    assert list(ds.data_vars) == ["foo"]


def test_ensure_dataset_data_array_no_name(
    vulnerability_curves: xr.Dataset,
):
    # Setup a data array without a name
    da = vulnerability_curves["default"].copy()
    da.name = None

    # Call the function with a name
    ds = ensure_dataset(da, name="foo")

    # Assert the output
    assert list(ds.data_vars) == ["foo"]


def test_ensure_dataset_errors(
    vulnerability_curves: xr.Dataset,
):
    # Setup a data array without a name
    da = vulnerability_curves["default"].copy()
    da.name = None

    # No name available at all
    with pytest.raises(
        ValueError,
        match="DataArray can't be set without a name",
    ):
        _ = ensure_dataset(da)

    # Wrong type
    with pytest.raises(
        TypeError,
        match="Wrong input data type: 'DataFrame'",
    ):
        _ = ensure_dataset(pd.DataFrame())
