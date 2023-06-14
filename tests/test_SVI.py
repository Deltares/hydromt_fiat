from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from hydromt.config import configread
from pathlib import Path
import pytest


DATASET = Path("C:\python\hydromt_fiat\local_test_database")
_cases = {
    "Test_SVI": {
        "folder": "test_hazard",
        "ini": "test_SVI.ini",
        "catalog": "fiat_catalog_hazard.yml",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
# @pytest.mark.skip(reason="Needs to be updated")
def test_SVI(case):
    # Read model in examples folder.
    root = DATASET.joinpath(_cases[case]["folder"])
    logger = setuplog("hydromt_fiat", log_level=10)
    config_fn = DATASET.joinpath(_cases[case]["ini"])
    data_libs = DATASET.joinpath(_cases[case]["catalog"])

    hyfm = FiatModel(root=root, mode="w", data_libs=data_libs, logger=logger)
    config = configread(config_fn)

    hyfm.build(opt=config)

    assert hyfm
