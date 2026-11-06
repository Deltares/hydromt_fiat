import pytest
from pydantic import ValidationError

from hydromt_fiat.settings.hazard import HazardVariable
from hydromt_fiat.utils import WATER__DEPTH


def test_base_model_f_update():
    # Setup the settings
    variable = HazardVariable(name="foo", type=WATER__DEPTH, rp=10)

    # Call the method with one setting
    variable.update(rp=50)

    # Assert the state, only the given setting is changed
    assert variable.rp == 50
    assert variable.name == "foo"
    assert variable.type == WATER__DEPTH


def test_base_model_f_update_none():
    # Setup the settings, without a return period
    variable = HazardVariable(name="foo", type=WATER__DEPTH)
    assert variable.rp is None

    # Call the method with a new setting
    variable.update(type="duration")

    # Assert the state
    assert variable.type == "duration"
    assert variable.rp is None


def test_base_model_f_update_errors():
    # Setup the settings
    variable = HazardVariable(name="foo", type=WATER__DEPTH)

    # Unknown settings are not allowed
    with pytest.raises(ValidationError):
        variable.update(bar=1)

    # Assert nothing is changed
    assert variable.type == WATER__DEPTH
