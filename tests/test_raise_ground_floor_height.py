from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil

EXAMPLEDIR = Path("P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database")

_cases = {
    "raise_ground_floor_height": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_read",
        "ini": EXAMPLEDIR / "test_read.ini",
        "ground_floor_height_reference": EXAMPLEDIR
        / "test_read"
        / "reference_groundHeight_test.shp",
        "new_root": EXAMPLEDIR / "test_raise_ground_floor_height",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_raise_ground_floor_height(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", logger=logger)

    fm.read()

    objectids = fm.exposure.get_object_ids(selection_type="all")
    fm.exposure.raise_ground_floor_height(
        raise_by=2,
        objectids=objectids,
        height_reference="geom",
        path_ref=_cases[case]["ground_floor_height_reference"],
        attr_ref="bfe",
    )

    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    fm.set_root(_cases[case]["new_root"])
    fm.write()
