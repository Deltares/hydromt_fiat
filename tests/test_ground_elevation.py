from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil
import copy


EXAMPLEDIR = Path().absolute() / "examples" / "data" / "update_ground_elevation"
DATADIR = Path().absolute() / "hydromt_fiat" / "data"

_cases = {
    "update_ground_elevation_with_dem": {
        "dir": "fiat_model",
        "new_root": EXAMPLEDIR / "test_update_ground_elevation",
        "ground_elevation_file": DATADIR 
        / "ground_elevation"
        / "charleston_14m.tif",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_ground_elevation(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(
        root=root, mode="r", logger=logger
    )

    fm.read()

    fm.exposure.setup_ground_elevation(
        _cases[case]["ground_elevation_file"],
    )

    # Remove the new root folder if it already exists
    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    # Set the new root and write the model
    fm.set_root(_cases[case]["new_root"])
    fm.write()

    assert 'Ground Elevation' in fm.exposure.exposure_db.columns, "The Ground Elevation was added"

