import logging
import re

import pandas as pd
import pytest

from hydromt_fiat.utils import OBJECT__TYPE
from hydromt_fiat.workflows.impact import filter_impact


def test_filter_impact(
    vulnerability_identifiers: pd.DataFrame,
):
    # Call the function
    v = filter_impact(
        vulnerability=vulnerability_identifiers,
        impact_type="damage",
    )

    # Assert the output
    assert len(v) == 8
    assert "residential" in v[OBJECT__TYPE].values


def test_filter_impact_list(
    caplog: pytest.LogCaptureFixture,
    vulnerability_identifiers: pd.DataFrame,
):
    caplog.set_level(logging.WARNING)
    # Call the function
    v = filter_impact(
        vulnerability=vulnerability_identifiers,
        impact_type=["damage", "affected"],
    )

    # Assert the output
    assert len(v) == 8
    assert "residential" in v[OBJECT__TYPE].values
    assert "No data found in the vulnerability identifiers" in caplog.text


def test_filter_impact_errors(
    vulnerability_identifiers: pd.DataFrame,
):
    # Ask for a nonsense impact type
    with pytest.raises(
        ValueError,
        match=re.escape(
            "No data found in the vulnerability identifiers for these \
impact types ['foo']",
        ),
    ):
        filter_impact(
            vulnerability=vulnerability_identifiers,
            impact_type="foo",
        )
