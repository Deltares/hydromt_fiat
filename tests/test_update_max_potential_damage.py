from hydromt_fiat.fiat import FiatModel
from pathlib import Path
import pytest
import shutil

EXAMPLEDIR = Path().absolute() / "local_test_database"

_cases = {
    "read": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_read",
        "ini": EXAMPLEDIR / "test_read.ini",
        "new_root": EXAMPLEDIR / "test_set_max_potential_damage",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_update_max_potential_damage(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])

    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(
        root=root,
        mode="r",
        data_libs=[data_catalog_yml],
    )

    fm.read()

    damage_cols = [
        fm.exposure.exposure_db.columns.get_loc(c)
        for c in fm.exposure.exposure_db.columns
        if "Max Potential Damage:" in c
    ]

    # Set the max potential damage to 0 for a few objects (buyout) and increase with 10% 'economic growth'
    updated_max_pot_damage = fm.exposure.exposure_db.copy()
    updated_max_pot_damage.iloc[:10, damage_cols] = 0
    print(
        f"Setting max pot damage of assets with Object ID {list(updated_max_pot_damage.iloc[:10, 0])} to 0."
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
