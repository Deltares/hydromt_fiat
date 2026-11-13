from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil
import pandas as pd

EXAMPLEDIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database"
)

_cases = {
    "raise_ground_floor_height_geom": {
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_raise_ground_floor_height_geom",
        "ground_floor_height_reference": EXAMPLEDIR
        / "test_read"
        / "reference_groundHeight_test.shp",
        "height_reference": "geom",
        "attr_ref": "bfe",
    },
    "raise_ground_floor_height_datum": {
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_raise_ground_floor_height_datum",
        "ground_floor_height_reference": None,
        "height_reference": "datum",
        "attr_ref": None,
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_raise_ground_floor_height(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", logger=logger)
    fm.read()

    # store original exposure
    exposure_original = fm.exposure.exposure_db

    objectids = fm.exposure.get_object_ids(selection_type="all")
    fm.exposure.raise_ground_floor_height(
        raise_by=2,
        objectids=objectids,
        height_reference=_cases[case]["height_reference"],
        path_ref=_cases[case]["ground_floor_height_reference"],
        attr_ref=_cases[case]["attr_ref"],
    )

    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    fm.set_root(_cases[case]["new_root"])
    fm.write()

    # read modified exposure
    exposure_modified = pd.read_csv(
        _cases[case]["new_root"] / "exposure" / "exposure.csv"
    )

    # check if buildings are raised
    assert all(
        gfh1 + ge1 <= gfh2 + ge2
        for gfh1, ge1, gfh2, ge2 in zip(
            exposure_original["ground_flht"],
            exposure_original["ground_elevtn"],
            exposure_modified["ground_flht"],
            exposure_modified["ground_elevtn"],
        )
    )
