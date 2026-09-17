import pandas as pd
import pytest

from hydromt_fiat.utils import COST__TYPE, VALUE
from hydromt_fiat.workflows import process_table


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
