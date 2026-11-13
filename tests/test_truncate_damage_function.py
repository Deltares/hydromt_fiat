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
    "truncate_damage_function": {
        "data_catalogue": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_truncate_damage_function",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_truncate_damage_function(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)
    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(root=root, mode="r", data_libs=[data_catalog_yml], logger=logger)
    fm.read()

    objectids_to_modify = [573783433, 573782415, 574268223, 574486724, 573785893]
    print(
        fm.exposure.exposure_db.loc[
            fm.exposure.exposure_db["object_id"].isin(objectids_to_modify),
            "fn_damage_structure",
        ].unique()
    )

    # store original exposure
    exposure_original = fm.exposure.exposure_db
    exposure_original_selection = exposure_original.loc[
        exposure_original["object_id"].isin(objectids_to_modify)
    ]

    fm.exposure.truncate_damage_function(
        objectids=objectids_to_modify,
        floodproof_to=2.5,
        damage_function_types=["structure", "content"],
        vulnerability=fm.vulnerability,
    )

    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    fm.set_root(_cases[case]["new_root"])
    fm.write()

    # read modified exposure
    exposure_modified = pd.read_csv(
        _cases[case]["new_root"] / "exposure" / "exposure.csv"
    )
    exposure_modified_selection = exposure_modified.loc[
        exposure_modified["object_id"].isin(objectids_to_modify)
    ]

    assert all(
        exposure_modified_selection["fn_damage_structure"]
        != exposure_original_selection["fn_damage_structure"]
    )
