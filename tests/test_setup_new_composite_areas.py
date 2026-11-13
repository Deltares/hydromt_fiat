from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil
import pandas as pd

EXAMPLEDIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database"
)
DATADIR = Path().absolute() / "hydromt_fiat" / "data"

_cases = {
    "setup_new_composite_area_datum": {
        "data_catalogue": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_setup_new_composite_area_datum",
        "composite_areas": EXAMPLEDIR / "test_read" / "new_development_area_test.gpkg",
        "type": "datum",
        "path_ref": None,
        "attr_ref": None,
    },
    "setup_new_composite_area_geom": {
        "data_catalogue": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "dir": "test_read",
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

    # store original exposure
    exposure_original = fm.exposure.exposure_db

    fm.exposure.setup_new_composite_areas(
        percent_growth=10,
        geom_file=str(_cases[case]["composite_areas"]),
        ground_floor_height=2,
        damage_types=["structure", "content"],
        vulnerability=fm.vulnerability,
        elevation_reference=_cases[case]["type"],
        path_ref=_cases[case]["path_ref"],
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

    # check if the new development area was added
    assert len(exposure_modified) > len(exposure_original)
