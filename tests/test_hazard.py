from hydromt_fiat.fiat import FiatModel
from hydromt_fiat.workflows.hazard import Hazard
from hydromt.config import configread
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
        "folder"   : "test_hazard_1",
        "ini"      : "test_hazard.ini",
        "catalog"  : "fiat_catalog_hazard.yml",

    }
}

@pytest.mark.parametrize("case", list(_cases.keys()))
def test_Hazard(case):
    # Read model in examples folder.
    root             = DATASET.joinpath(_cases[case]["folder"])
    config_fn        = DATASET.joinpath(_cases[case]["ini"])
    data_libs        = DATASET.joinpath(_cases[case]["catalog"])

    hyfm = FiatModel(root=root, mode="w", data_libs=data_libs, config_fn=config_fn)

    map_fn         = configread(config_fn)['setup_hazard']['map_fn']
    map_type       = configread(config_fn)['setup_hazard']['map_type']
    rp             = configread(config_fn)['setup_hazard']['rp']
    crs            = configread(config_fn)['setup_hazard']['crs']
    nodata         = configread(config_fn)['setup_hazard']['nodata']
    var            = configread(config_fn)['setup_hazard']['var']
    chunks         = configread(config_fn)['setup_hazard']['chunks']
    maps_id        = configread(config_fn)['setup_hazard']['maps_id']
    name_catalog   = configread(config_fn)['setup_hazard']['name_catalog']
    risk_output    = configread(config_fn)['setup_hazard']['risk_output']
    hazard_type    = configread(config_fn)['setup_config']['hazard_type']

    hyfm_hazard = Hazard()

    hyfm_hazard.checkInputs(
        hyfm,
        map_fn,
        map_type,
        chunks,
        rp,
        crs,
        nodata,
        var,
    )

    ds = hyfm_hazard.readMaps(
        hyfm,
        name_catalog,
        hazard_type,
        risk_output,
        crs,
        nodata,
        var,
        chunks,
    )
    
    assert hyfm


