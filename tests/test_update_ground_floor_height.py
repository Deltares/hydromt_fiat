from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil


EXAMPLEDIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database"
)
DATADIR = Path().absolute() / "hydromt_fiat" / "data"

_cases = {
    "update_ground_floor_height": {
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_update_ground_floor_height",
        "data_catalog": DATADIR / "hydromt_fiat_catalog_USA.yml",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_update_ground_floor_height(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", data_libs=[_cases[case]["data_catalog"]], logger=logger)
    fm.read()

    ground_floor_height_file = EXAMPLEDIR / "data" / "ground_floor_height" / "fake_elevation_certificates.gpkg"
    attribute = "FFE"
    method = "nearest"

    fm.exposure.setup_ground_floor_height(ground_floor_height_file, attribute, method)

    # Remove the new root folder if it already exists
    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    # Set the new root and write the model
    fm.set_root(_cases[case]["new_root"])
    fm.write()
