from hydromt_fiat.fiat import FiatModel
from pathlib import Path
import pytest


EXAMPLEDIR = Path("P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database")

_cases = {
    "read": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_read",
        "ini": EXAMPLEDIR / "test_read.ini",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_read_fiat_config(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])

    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(
        root=root,
        mode="r",
        data_libs=[data_catalog_yml],
    )

    fm.read()
