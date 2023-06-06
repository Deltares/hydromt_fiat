from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil

EXAMPLEDIR = Path().absolute() / "local_test_database"

_cases = {
    "setup_new_composite_area_datum": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_read",
        "ini": EXAMPLEDIR / "test_read.ini",
        "new_root": EXAMPLEDIR / "test_setup_new_composite_area_datum",
        "composite_areas": EXAMPLEDIR / "test_read" / "new_development_area_test.gpkg",
        "type": "datum",
        "path_ref": None,
        "attr_ref": None,
    },
    "setup_new_composite_area_geom": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_read",
        "ini": EXAMPLEDIR / "test_read.ini",
        "new_root": EXAMPLEDIR / "test_setup_new_composite_area_geom",
        "composite_areas": EXAMPLEDIR / "test_read" / "new_development_area_test.gpkg",
        "type": "geom",
        "path_ref": EXAMPLEDIR / "test_read" / "reference_groundHeight_test.shp",
        "attr_ref": "bfe",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_setup_new_composite_areas_datum(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)
    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(root=root, mode="r", data_libs=[data_catalog_yml], logger=logger)

    fm.read()

    fm.exposure.setup_new_composite_areas(
        percent_growth=10,
        geom_file=str(_cases[case]["composite_areas"]),
        ground_floor_height=2,
        damage_types=["Structure"],
        vulnerability=fm.vulnerability,
        elevation_reference=_cases[case]["type"],
        path_ref=_cases[case]["path_ref"],
        attr_ref=_cases[case]["attr_ref"],
    )

    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    fm.set_root(_cases[case]["new_root"])
    fm.write()
