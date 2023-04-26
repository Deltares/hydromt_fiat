from hydromt_fiat.fiat import FiatModel
from pathlib import Path
import pytest

EXAMPLEDIR = Path().absolute() / "examples"
DATASET     = Path("P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database")

_cases = {
    # "fiat_flood": {
    #     "region_grid": Path("data").joinpath("flood_hand", "hand_050cm_rp02.tif"),
    #     "example"    : "fiat_flood",
    #     "ini"        : "fiat_flood.ini",
    # },

    "fiat_objects": {
        "folder"   : "test_hazard",
        "ini"      : "test_hazard.ini",
        "catalog"  : "fiat_catalog_hazard.yml",

    },
}

@pytest.mark.parametrize("case", list(_cases.keys()))

def test_Hazard(case):
    # Read model in examples folder.
    root             = DATASET.joinpath(_cases[case]["folder"])
    config_fn        = DATASET.joinpath(_cases[case]["ini"])
    data_libs        = DATASET.joinpath(_cases[case]["catalog"])

    hyfm = FiatModel(root=root, mode="r", data_libs=data_libs, config_fn=config_fn)

    # raster_max_depth    = hyfm.data_catalog.get_rasterdataset("max_depth")
    # flood_maps_varaible = hyfm.data_catalog.get_rasterdataset("flood_maps_varaible")
    # hazard_type         = hyfm.get_config('setup_config', 'hazard_type')

    # hyfm.setup_hazard()

    assert hyfm



