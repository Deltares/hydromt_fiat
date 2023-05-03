from hydromt_fiat.fiat import FiatModel
from hydromt.config import configread
from pathlib import Path
import pytest


EXAMPLEDIR = Path().absolute() / "local_test_database"
_cases = {
    "fiat_objects": {
        "folder": "test_hazard",
        "ini": "test_SVI.ini",
        "catalog": "fiat_catalog_hazard.yml",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
@pytest.mark.skip(reason="Needs to be updated")
def test_SVI(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["folder"])
    config_fn = EXAMPLEDIR.joinpath(_cases[case]["ini"])
    data_libs = EXAMPLEDIR.joinpath(_cases[case]["catalog"])

    hyfm = FiatModel(root=root, mode="w", data_libs=data_libs)
    config = configread(config_fn)

    hyfm.build(opt=config)

    assert hyfm
