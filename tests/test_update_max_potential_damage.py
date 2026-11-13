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
    "update_max_potential_damage": {
        "data_catalogue": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_update_max_potential_damage",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_update_max_potential_damage(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", logger=logger)

    fm.read()

    damage_cols = [
        fm.exposure.exposure_db.columns.get_loc(c)
        for c in fm.exposure.exposure_db.columns
        if "max_damage_" in c
    ]

    # Set the max potential damage to 0 for a few objects (buyout) and increase with 10% 'economic growth'
    updated_max_pot_damage = fm.exposure.exposure_db.copy()
    updated_max_pot_damage.iloc[:10, damage_cols] = 0
    print(
        f"Setting max pot damage of assets with object_id {list(updated_max_pot_damage.iloc[:10, 0])} to 0."
    )
    updated_max_pot_damage.iloc[:, damage_cols] = (
        updated_max_pot_damage.iloc[:, damage_cols] * 1.01
    )

    fm.exposure.update_max_potential_damage(
        updated_max_potential_damages=updated_max_pot_damage
    )

    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    fm.set_root(_cases[case]["new_root"])
    fm.write()

    # read modified exposure
    exposure_modified = pd.read_csv(
        _cases[case]["new_root"] / "exposure" / "exposure.csv"
    )

    # check if the max potential damage is updated
    updated_max_pot_damage.reset_index(inplace=True, drop=True)
    updated_max_pot_damage["object_name"] = updated_max_pot_damage[
        "object_name"
    ].astype(int)

    # Add object_id to df
    updated_max_pot_damage["object_id"] = updated_max_pot_damage["object_name"]
    cols = ["object_id"] + [col for col in updated_max_pot_damage if col != "object_id"]
    updated_max_pot_damage = updated_max_pot_damage[cols]

    pd.testing.assert_frame_equal(
        updated_max_pot_damage,
        exposure_modified,
        check_dtype=False,
        check_column_type=False,
    )
