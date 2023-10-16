from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil

EXAMPLEDIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database"
)

_cases = {
    "event_map": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_event_map",
        "configuration": {
        "setup_hazard": {
            "map_fn": [
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\RP_1_maps.nc",
            ],
            "map_type": "water_depth",
            "rp": None,
            "crs": None,
            "nodata": -99999,
            "var": "zsmax",
            "risk_output": False,
        }
    }
    },
    "risk_map": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_risk_map",
        "configuration": {
        "setup_hazard": {
            "map_fn": [
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\RP_1_maps.nc",
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\RP_50_maps.nc",
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\RP_10_maps.nc",
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\RP_100_maps.nc",
            ],
            "map_type": "water_depth",
            "rp": None,
            "crs": None,
            "nodata": -99999,
            "var": "zsmax",
            "risk_output": True,
        }
    }
    },

    "event_map_geotiffs": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_event_map_geotiffs",
        "configuration": {
        "setup_hazard": {
            "map_fn": [
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\Swell_Majuro_case_SW_slr_100_RP1_Final.tif",
            ],
            "map_type": "water_depth",
            "rp": None,
            "crs": None,
            "nodata": None,
            "var": None,
            "risk_output": False,
        }
    }
    },

    "risk_map_geotiffs": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_risk_map_geotiffs",
        "configuration": {
        "setup_hazard": {
            "map_fn": [
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\Swell_Majuro_case_SW_slr_100_RP1_Final.tif",
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\Swell_Majuro_case_SW_slr_100_RP10_Final.tif",
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\Swell_Majuro_case_SW_slr_100_RP50_Final.tif",
            ],
            "map_type": "water_depth",
            "rp": None,
            "crs": None,
            "nodata": None,
            "var": None,
            "risk_output": True,
        }
    }
    },

    "event_map_geotiff2": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_event_map_geotiff2",
        "configuration": {
        "setup_hazard": {
            "map_fn": [
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\kingTide_SLR_max_flood_depth.tif",
            ],
            "map_type": "water_depth",
            "rp": None,
            "crs": None,
            "nodata": None,
            "var": None,
            "risk_output": False,
        }
    }
    },

    "risk_map_geotiff2": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_risk_map_geotiff2",
        "configuration": {
        "setup_hazard": {
            "map_fn": [
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth.tif",
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\Current_prob_event_set_combined_doNothing_withSeaWall_RP=10_max_flood_depth.tif",
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\Current_prob_event_set_combined_doNothing_withSeaWall_RP=100_max_flood_depth.tif",              
            ],
            "map_type": "water_depth",
            "rp": None,
            "crs": None,
            "nodata": None,
            "var": None,
            "risk_output": True,
        }
    }
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_hazard(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    if root.exists():
        shutil.rmtree(root)

    logger = setuplog("hydromt_fiat", log_level=10)
    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(root=root, mode="w", data_libs=[data_catalog_yml], logger=logger)
    region = fm.data_catalog.get_geodataframe("region", variables=None)
    
    fm.build(region={"geom": region}, opt=_cases[case]["configuration"])
    fm.write()

    # Check if the hazard folder exists
    assert root.joinpath("hazard").exists()
