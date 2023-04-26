from hydromt_fiat.fiat import FiatModel
from pathlib import Path
import pytest
import shutil

EXAMPLEDIR = Path().absolute() / "local_test_database"

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

    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(
        root=root,
        mode="r",
        data_libs=[data_catalog_yml],
    )

    fm.read()

    objectids_to_modify = "all"
    fm.exposure.raise_ground_floor_height(
        objectids=objectids_to_modify,
        raise_by=2,
        height_reference="geom",
        reference_geom_path=_cases[case]["ground_floor_height_reference"],
        reference_geom_attrname="bfe",
    )

    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    fm.set_root(_cases[case]["new_root"])
    fm.write()
