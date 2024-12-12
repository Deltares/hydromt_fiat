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
AGGRDIR = Path().resolve() / "examples" / "data" / "aggregation_zones"
DATADIRDEM = Path(
    "P:/11207949-dhs-phaseii-floodadapt/FloodAdapt/Test_data/Database_env_fix/static/dem"
)

_cases = {
    "setup_new_composite_area_elevation_aggregation": {
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_setup_new_composite_area_elevation_aggregation",
        "composite_areas": DATADIR
        / "new_composite_areas"
        / "new_development_area_aggregation_test.gpkg",
        "type": "datum",
        "path_ref": None,
        "attr_ref": None,
        "ground_elevation": DATADIRDEM
        / "charleston_14m.tif",
        "aggregation_area_fn": [
            AGGRDIR / "aggregation_zones" / "council.gpkg",
            AGGRDIR / "aggregation_zones" / "base_zones.gpkg",
            AGGRDIR / "aggregation_zones" / "land_use.gpkg",
        ],
        "attribute_names": ["LONGNAME", "ZONE_BASE", "LAND_USE"],
        "label_names": ["Council", "Zoning_map", "Land_use_map"],
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_setup_new_composite_areas_ground_elevation_aggregation(case):
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
    assert not exposure_modified.duplicated("object_id").values.all()

    # Check if max potentail damages are divided correctly
    exposure_new_composite = exposure_modified[
        exposure_modified["primary_object_type"] == "New development area"
    ]
    assert round(sum([38142538.34, 13528445.7])) == round(
        sum(exposure_new_composite["max_damage_content"].values)
    )
    assert round(sum([61681912.36, 21877421.83])) == round(
        sum(exposure_new_composite["max_damage_structure"].values)
    )
