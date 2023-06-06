from hydromt_fiat.fiat import FiatModel
from hydromt_fiat.workflows.hazard import *
from hydromt.config import configread
from pathlib import Path
import pytest

DATASET     = Path("P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database")

_cases = {

    "fiat_objects": {
        "folder": "test_hazard_1",
        "ini": "test_hazard.ini",
        "catalog": "fiat_catalog_hazard.yml",
    }
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_Hazard(case):
    # Read model in examples folder.
    root = DATASET.joinpath(_cases[case]["folder"])
    config_fn = DATASET.joinpath(_cases[case]["ini"])
    data_libs = DATASET.joinpath(_cases[case]["catalog"])

    logger = setuplog("hydromt_fiat", log_level=10)
    hyfm = FiatModel(
        root=root, mode="w", data_libs=data_libs, config_fn=config_fn, logger=logger
    )

    map_fn = configread(config_fn)["setup_hazard"]["map_fn"]
    map_type = configread(config_fn)["setup_hazard"]["map_type"]
    rp = configread(config_fn)["setup_hazard"]["rp"]
    crs = configread(config_fn)["setup_hazard"]["crs"]
    nodata = configread(config_fn)["setup_hazard"]["nodata"]
    var = configread(config_fn)["setup_hazard"]["var"]
    chunks = configread(config_fn)["setup_hazard"]["chunks"]
    configread(config_fn)["setup_hazard"]["maps_id"]
    name_catalog = configread(config_fn)["setup_hazard"]["name_catalog"]
    risk_output = configread(config_fn)["setup_hazard"]["risk_output"]
    hazard_type = configread(config_fn)["setup_config"]["hazard_type"]

    param_lst = get_lists(
        map_fn,
        map_type,
        chunks,
        rp,
        crs,
        nodata,
        var,
    )

    check_parameters(
        param_lst,
        hyfm,
        chunks,
        rp,
        crs,
        nodata,
        var,
    )

    process_maps(
        param_lst,
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


