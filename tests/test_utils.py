import io
import sys
from pathlib import Path

import numpy as np
from barril.units import Scalar

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
    assert out.count("\n") == 34
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
    assert out.count("\n") == 10
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
    assert out.count("\n") == 7
    assert "data_catalog.yml" not in out


def test_standard_unit_equal():
    unit = Scalar(1.0, "m")
    scalar = standard_unit(unit)

    assert np.isclose(scalar.value, 1.0)
    assert scalar.unit == "m"


def test_standard_unit_length():
    unit = Scalar(1.0, "ft")
    scalar = standard_unit(unit)

    assert np.isclose(scalar.value, 0.3048)
    assert scalar.unit == ""
