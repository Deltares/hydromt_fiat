from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import numpy as np
import pytest
import shutil
import copy


EXAMPLEDIR = Path().absolute() / "examples" / "data" / "update_ground_elevation"
DATADIR = Path().absolute() / "hydromt_fiat" / "data"
DATADIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/FloodAdapt/Test_data/Database_env_fix/static/dem"
)

_cases = {
    "update_ground_elevation_with_dem": {
        "dir": "fiat_model",
        "new_root": EXAMPLEDIR / "test_update_ground_elevation",
        "ground_elevation_file": DATADIR 
        / "charleston_14m.tif",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_ground_elevation(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(
        root=root, mode="r", logger=logger
    )

    fm.read()

    original_exposure = copy.deepcopy(fm.exposure.exposure_db)
    unique_ge_original = original_exposure["Ground Elevation"].unique()

    fm.exposure.setup_ground_elevation(
        _cases[case]["ground_elevation_file"],
        fm.exposure.exposure_db,
        fm.exposure.get_full_gdf(fm.exposure.exposure_db),
    )

    # Remove the new root folder if it already exists
    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    # Set the new root and write the model
    fm.set_root(_cases[case]["new_root"])
    fm.write()

    unique_ge_new = fm.exposure.exposure_db["Ground Elevation"].unique()
    assert not np.array_equal(unique_ge_original, unique_ge_new), "The Ground Elevation is the same"

