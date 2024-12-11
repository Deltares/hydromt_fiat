from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil
import pandas as pd

EXAMPLEDIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database"
)

EXAMPLEDIR = Path().absolute() / "examples" / "data" / "setup_new_composite_area"
DATADIR = Path().absolute() / "hydromt_fiat" / "data"
DATADIRDEM = Path(
    "P:/11207949-dhs-phaseii-floodadapt/FloodAdapt/Test_data/Database_env_fix/static/dem"
)

_cases = {
    "setup_new_composite_area_datum": {
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_setup_new_composite_area_datum",
        "composite_areas": DATADIR
        / "new_composite_areas"
        / "new_development_area_test.gpkg",
        "type": "datum",
        "path_ref": None,
        "attr_ref": None,
        "ground_elevation": None,
        "aggregation_area_fn": None,
        "attribute_names": None,
        "label_names": None,
    },
    "setup_new_composite_area_geom": {
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_setup_new_composite_area_geom",
        "composite_areas": DATADIR
        / "new_composite_areas"
        / "new_development_area_test.gpkg",
        "type": "geom",
        "path_ref": DATADIR / "new_composite_areas" / "reference_groundHeight_test.shp",
        "attr_ref": "bfe",
        "ground_elevation": None,
        "aggregation_area_fn": None,
        "attribute_names": None,
        "label_names": None,
    },
    "setup_new_composite_area_elevation": {
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_setup_new_composite_area_elevation",
        "composite_areas": DATADIR
        / "new_composite_areas"
        / "new_development_area_test.gpkg",
        "type": "datum",
        "path_ref": None,
        "attr_ref": None,
        "ground_elevation": DATADIRDEM / "charleston_14m.tif",
        "aggregation_area_fn": EXAMPLEDIR.joinpath(
            "test_read", "exposure", "aggregation_areas", "block_groups.gpkg"
        ),
        "attribute_names": "GEOID_short",
        "label_names": "Aggregation Label: Census Block",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_setup_new_composite_areas_ground_elevation(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", logger=logger)
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
        ground_elevation=_cases[case]["ground_elevation"],
        aggregation_area_fn=_cases[case]["aggregation_area_fn"],
        attribute_names=_cases[case]["attribute_names"],
        label_names=_cases[case]["label_names"],
    )

    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    fm.set_root(_cases[case]["new_root"])
    fm.write()

    # read modified exposure
    exposure_modified = pd.read_csv(
        _cases[case]["new_root"] / "exposure" / "exposure.csv"
    )

    exposure_modified = fm.exposure.exposure_db

    # check if the new development area was added
    assert len(exposure_modified) > len(
        exposure_original
    ), "The composite areas were not added"