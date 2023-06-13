from hydromt_fiat.fiat import FiatModel
from hydromt.config import configread
from pathlib import Path
import pytest
import shutil


EXAMPLEDIR = Path().absolute() / "local_test_database"

_cases = {
    "vulnerability_and_exposure": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_exposure",
        "ini": EXAMPLEDIR / "test_vulnerability_and_exposure.ini",
    },
    "vulnerability_and_exposure": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_exposure",
        "ini": EXAMPLEDIR / "test_vulnerability_and_exposure.ini",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_exposure(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    if root.exists:
        shutil.rmtree(root)
    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(
        root=root,
        mode="w",
        data_libs=[data_catalog_yml],
    )

    region = fm.data_catalog.get_geodataframe("region", variables=None)
    opt = configread(_cases[case]["ini"])
    fm.build(region={"geom": region}, opt=opt)
    fm.write()