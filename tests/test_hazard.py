from hydromt_fiat.fiat import FiatModel
from pathlib import Path
import pytest

EXAMPLEDIR = Path().absolute() / "examples"
DATASET     = Path("p:/11207058-fiat-objects-interface/FiatModelBuilder/Model_Builder")
#DATASET     = Path("C:/Users/fuentesm/CISNE/HydroMT_sprint_sessions/Model_Builder") 

_cases = {
    # "fiat_flood": {
    #     "region_grid": Path("data").joinpath("flood_hand", "hand_050cm_rp02.tif"),
    #     "example"    : "fiat_flood",
    #     "ini"        : "fiat_flood.ini",
    # },

    "fiat_objects": {
        "folder"   : "test_hazard",
        "ini"      : "test_hazard.ini",
        "flood_map":  Path("Hazard").joinpath("kingTide_SLR_max_flood_depth.tif"),
        "catalog"  : "fiat_catalog_hazard.yml",

    },
}

@pytest.mark.parametrize("case", list(_cases.keys()))

def test_Hazard(case):
    # Read model in examples folder.
    root             = DATASET.joinpath(_cases[case]["folder"])
    config_fn        = DATASET.joinpath(_cases[case]["ini"])
    data_libs        = DATASET.joinpath(_cases[case]["catalog"])
    root_raster      = DATASET.joinpath(_cases[case]["flood_map"])



    hyfm = FiatModel(root=root, mode="r", data_libs=data_libs, config_fn=config_fn)
    hyfm.setup_hazard()

    raster_max_depth = hyfm.data_catalog.get_rasterdataset("max_depth")
    hazard_type      = hyfm.get_config('setup_config', 'hazard_type')

    assert hyfm



