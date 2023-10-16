from typing import Sequence
from _pytest.mark.structures import ParameterSet
from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil

#Datasource: https://github.com/microsoft/USBuildingFootprints

EXAMPLEDIR = Path().resolve() / "examples" / "data" / "building_footprints"

#Create test
_cases = {
    "join_building_footprints_to_exposure": {
        "root": EXAMPLEDIR / "fiat_model",
        "new_root":  EXAMPLEDIR / "fiat_model_bfs",
        "configuration": {
            "setup_building_footprint": {
                "building_footprint_fn": EXAMPLEDIR / "building_footprints" / "building_footprints.gpkg",
                "attribute_name": "BF_FID",
                }
        },
    }
}

# Set up Fiat Model
@pytest.mark.parametrize("case", list(_cases.keys()))
def test_building_footprints(case: ParameterSet | Sequence[object] | object):
    # Read model in examples folder.
    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=_cases[case]["root"], mode="r", logger=logger)
    fm.read()

    fm.build(write=False, opt=_cases[case]["configuration"])
    fm.set_root(_cases[case]["new_root"])
    fm.write()

    # Check if the BF_FID column is added
    assert "BF_FID" in fm.exposure.exposure_db.columns

    # Check for Object ID duplicates
    assert fm.exposure.exposure_db["Object ID"].duplicated().sum() == 0
