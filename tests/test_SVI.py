from hydromt_fiat.fiat import FiatModel
from pathlib import Path
import pytest


DATASET     = Path("p:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database")
_cases = {
    # "fiat_flood": {
    #     "region_grid": Path("data").joinpath("flood_hand", "hand_050cm_rp02.tif"),
    #     "example"    : "fiat_flood",
    #     "ini"        : "fiat_flood.ini",
    # },

    "fiat_objects": {
        "folder"   : "test_hazard",
        "ini"      : "test_SVI.ini",
        "catalog"  : "fiat_catalog_hazard.yml",

    },
}

@pytest.mark.parametrize("case", list(_cases.keys()))

def test_SVI(case):


    # Read model in examples folder.
    root             = DATASET.joinpath(_cases[case]["folder"])
    config_fn        = DATASET.joinpath(_cases[case]["ini"])
    data_libs        = DATASET.joinpath(_cases[case]["catalog"])

    hyfm = FiatModel(root=root, mode="r", data_libs=data_libs, config_fn=config_fn)

    hyfm.setup_social_vulnerability_index()

    df= hyfm.df_scores

    assert hyfm
