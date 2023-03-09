from hydromt_fiat.fiat import FiatModel
from pathlib import Path

EXAMPLEDIR = Path().absolute() / "examples"


def test_read():
    # First remove the output folders?

    root = EXAMPLEDIR.joinpath("fiat_flood")
    fm = FiatModel(root=root, mode="r")
    fm.read()

    # Assert that all the configurations are read in correctly
    assert fm.config["strategy"] == "base"
    assert fm.config["scenario"] == "base"
    assert fm.config["year"] == 2021
    assert fm.config["country"] == "ITA"
    assert fm.config["hazard_type"] == "flooding"
    assert fm.config["output_unit"] == "USD"
    assert fm.config["hazard_dp"] == root / "hazard"
    assert fm.config["exposure_dp"] == root / "exposure"
    assert fm.config["susceptibility_dp"] == "susceptibility"
    assert fm.config["output_dp"] == root / "output"
    assert fm.config["category_output"] is True
    assert fm.config["total_output"] is True
    assert fm.config["risk_output"] is True
    assert fm.config["map_output"] is True
    assert fm.config["vulnerability_dp"] == root / "vulnerability"
    assert fm.config["hazard"]["water_depth"]["hand_050cm_rp02"]["usage"] is True
    assert (
        fm.config["hazard"]["water_depth"]["hand_050cm_rp02"]["map_fn"]
        == root / "hazard/hand_050cm_rp02.tif"
    )
    assert (
        fm.config["hazard"]["water_depth"]["hand_050cm_rp02"]["map_type"]
        == "water_depth"
    )
    assert fm.config["hazard"]["water_depth"]["hand_050cm_rp02"]["rp"] == 2
    assert fm.config["hazard"]["water_depth"]["hand_050cm_rp02"]["crs"] == "EPSG:4326"
    assert fm.config["hazard"]["water_depth"]["hand_050cm_rp02"]["nodata"] == -9999
    assert fm.config["hazard"]["water_depth"]["hand_050cm_rp02"]["var"] is None
    assert fm.config["hazard"]["water_depth"]["hand_050cm_rp02"]["chunks"] == 100

    assert fm.config["hazard"]["water_depth"]["hand_150cm_rp50"]["usage"] is True
    assert (
        fm.config["hazard"]["water_depth"]["hand_150cm_rp50"]["map_fn"]
        == root / "hazard/hand_150cm_rp50.tif"
    )
    assert (
        fm.config["hazard"]["water_depth"]["hand_150cm_rp50"]["map_type"]
        == "water_depth"
    )
    assert fm.config["hazard"]["water_depth"]["hand_150cm_rp50"]["rp"] == 50
    assert fm.config["hazard"]["water_depth"]["hand_150cm_rp50"]["crs"] == "EPSG:4326"
    assert fm.config["hazard"]["water_depth"]["hand_150cm_rp50"]["nodata"] == -9999
    assert fm.config["hazard"]["water_depth"]["hand_150cm_rp50"]["var"] is None
    assert fm.config["hazard"]["water_depth"]["hand_150cm_rp50"]["chunks"] == 100
