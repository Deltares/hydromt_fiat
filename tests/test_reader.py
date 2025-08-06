import pytest
from hydromt.log import setuplog

from hydromt_fiat.fiat import FiatModel
from hydromt_fiat.workflows.exposure_vector import ExposureVector
from hydromt_fiat.workflows.vulnerability import Vulnerability
from tests.conftest import P_DRIVE_TEST_DB

_cases = {
    "read": {
        "dir": "test_read",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_read(case):
    # Read model in examples folder.
    root = P_DRIVE_TEST_DB.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", logger=logger)
    fm.read()

    # Check if the exposure object exists
    assert isinstance(fm.exposure, ExposureVector)

    # Check if the exposure database exists
    assert not fm.exposure.exposure_db.empty

    # Check if the vulnerability object exists
    assert isinstance(fm.vulnerability, Vulnerability)

    # Check if the vulnerability functions exist
    assert len(fm.vulnerability.functions) > 0
