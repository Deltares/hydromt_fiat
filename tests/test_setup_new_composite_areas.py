from hydromt_fiat.fiat import FiatModel
from pathlib import Path
import pytest
import shutil

EXAMPLEDIR = Path().absolute() / "local_test_database"

_cases = {
    "setup_new_composite_area": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_read",
        "ini": EXAMPLEDIR / "test_read.ini",
        "new_root": EXAMPLEDIR / "test_setup_new_composite_area",
        "composite_areas": EXAMPLEDIR / "new_development_area_test.gpkg",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_setup_new_composite_areas(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])

    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(
        root=root,
        mode="r",
        data_libs=[data_catalog_yml],
    )

    fm.read()
    
    fm.exposure.setup_new_composite_areas(
         percent_growth=10,
         geom_file=str(_cases[case]["composite_areas"]),
         ground_floor_height=2
         damage_types=['Structure'],
         vulnerability=fm.vulnerability
    )

    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    fm.set_root(_cases[case]["new_root"])
    fm.write()
