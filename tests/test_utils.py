import io
import logging
import sys
from pathlib import Path

import numpy as np
import pytest

from hydromt_fiat.utils import (
    create_query,
    directory_tree,
    standard_unit,
)


def test_create_query_single_type():
    # Single values only
    query = create_query(
        var1="value",
        var2=2,
    )
    assert query == "var1 == 'value' and var2 == 2"


def test_create_query_combined_type():
    # Single value and an iterator (list)
    query = create_query(
        var1="value",
        var2=[1, 2, 3],
    )
    assert query == "var1 == 'value' and var2 in [1, 2, 3]"


def test_create_query_iter_type():
    # Lists only
    query = create_query(
        var1=["value1", "value2"],
        var2=[1, 2],
    )
    assert query == "var1 in ['value1', 'value2'] and var2 in [1, 2]"


def test_directory_tree(build_data_path: Path):
    # Redirect the stdout to a buffer
    s = io.StringIO()
    sys.stdout = s

    # Call the function
    directory_tree(build_data_path)

    # Reset the buffer to view the output
    s.seek(0)
    out = s.read()
    # Assert the output
    assert out.count("\n") == 22
    assert "data_catalog.yml" in out


def test_directory_tree_level(build_data_path: Path):
    # Redirect the stdout to a buffer
    s = io.StringIO()
    sys.stdout = s

    # Call the function
    directory_tree(build_data_path, level=1)

    # Reset the buffer to view the output
    s.seek(0)
    out = s.read()
    # Assert the output
    assert out.count("\n") == 9
    assert "data_catalog.yml" in out


def test_directory_tree_dirs_only(build_data_path: Path):
    # Redirect the stdout to a buffer
    s = io.StringIO()
    sys.stdout = s

    # Call the function
    directory_tree(build_data_path, limit_to_directories=True)

    # Reset the buffer to view the output
    s.seek(0)
    out = s.read()
    # Assert the output
    assert out.count("\n") == 6
    assert "data_catalog.yml" not in out


def test_standard_unit_equal():
    # Call the function with the standard for length as input
    unit = "m"
    quantity = standard_unit(unit)

    # Assert magnitude is 1
    assert np.isclose(quantity.magnitude, 1.0)
    assert str(quantity.units) == "meter"


def test_standard_unit_length(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.WARNING)
    # Call the function with feet as unit
    unit = "ft"
    quantity = standard_unit(unit)

    # Assert conversion
    assert np.isclose(quantity.magnitude, 0.3048)
    assert str(quantity.units) == "meter"
    assert "Given unit (foot) does not match the standard unit (meter)" in caplog.text
