from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil
import copy
import numpy as np


EXAMPLEDIR = Path().absolute() / "examples" / "data" / "update_max_potential_damage"
DATADIR = Path().absolute() / "hydromt_fiat" / "data"

_cases = {
    "update_max_potential_damage_with_points": {
        "dir": "fiat_model",
        "new_root": EXAMPLEDIR / "test_update_max_potential_damage_points",
        "data_catalog": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "max_potential_damage_file": EXAMPLEDIR
        / "fake_max_potential_damage_points.gpkg",
        "damage_types": "content",
        "attribute": "maxpotential_content",
        "method_damages": "nearest",
        "max_dist": 50,
    },
    "update_max_potential_damage_with_polygons": {
        "dir": "fiat_model",
        "new_root": EXAMPLEDIR / "test_update_max_potential_damage_polygons",
        "data_catalog": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "max_potential_damage_file": EXAMPLEDIR
        / "fake_max_potential_damage_polygons.gpkg",
        "damage_types": "structure",
        "attribute": "maxpotential_structure",
        "method_damages": "intersection",
        "max_dist": None,
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_update_max_potential_damage(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(
        root=root, mode="r", data_libs=[_cases[case]["data_catalog"]], logger=logger
    )
    fm.read()

    target_column = f"max_damage_{_cases[case]['damage_types']}"

    original_exposure = copy.deepcopy(fm.exposure.exposure_db)
    unique_mp_original = original_exposure[target_column].unique()

    fm.exposure.setup_max_potential_damage(
        max_potential_damage=_cases[case]["max_potential_damage_file"],
        damage_types=_cases[case]["damage_types"],
        attribute_name=_cases[case]["attribute"],
        method_damages=_cases[case]["method_damages"],
        max_dist=_cases[case]["max_dist"],
    )

    # Remove the new root folder if it already exists
    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    # Set the new root and write the model
    fm.set_root(_cases[case]["new_root"])
    fm.write()

    # Check if the new maximun potential damage is different from the original one
    unique_mp_new = fm.exposure.exposure_db[target_column].unique()
    assert not np.array_equal(
        unique_mp_original, unique_mp_new
    ), "The maximun potential damage is the same"
