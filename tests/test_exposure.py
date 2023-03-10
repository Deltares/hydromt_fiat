from hydromt_fiat.fiat import FiatModel
from pathlib import Path
import pytest

EXAMPLEDIR = Path().absolute() / "local_test_database"

_cases = {
    "exposure": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_exposure",
        "ini": EXAMPLEDIR / "test_exposure.ini",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_exposure(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(
        root=root,
        mode="r",
        data_libs=[data_catalog_yml],
        config_fn=_cases[case]["ini"],
    )
    fm.read()

    region = fm.data_catalog.get_geodataframe("region", variables=None)
    fm.setup_basemaps({"geom": region})

    fm.setup_exposure_vector(fm.region)
