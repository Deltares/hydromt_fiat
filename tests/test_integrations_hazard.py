from hydromt_fiat.fiat import FiatModel
from hydromt.config import configread
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil
import os

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

    "event_map_geotiff_kath": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_event_map_geotiff_kath",
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

    "risk_map_geotiff_kath": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_risk_map_geotiff_kath",
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

    "event_map_sfincs_willem": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_event_map_sfincs_willem",
        "configuration": {
        "setup_hazard": {
            "map_fn": [
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\overland\sfincs_map.nc"
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
    
    "event_map_sfincs_phanos": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_event_map_sfincs_phanos",
        "configuration": {
        "setup_hazard": {
            "map_fn": [
                r"P:\11207949-dhs-phaseii-floodadapt\Model-builder\Delft-FIAT\local_test_database\test_RP_floodmaps\charleston\output\simulations\current_extreme12ft_no_measures\overland\sfincs_map.nc"
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


    # for these test data sfincs output data is required in local files
    # uncomment to test event analysis from sfincs output
    # mode = "single"
    # map_path = Path("C:/Users/fuentesm/CISNE/Deltares/FloodAdapt/tests/test_database/charleston/output/simulations/current_extreme12ft_no_measures/overland")

    # uncomment to test risk analysis from sfincs outputs
    # mode = "risk"
    # map_path = Path("C:/Users/fuentesm/CISNE/Deltares/FloodAdapt/tests/test_database/charleston/output/simulations/current_test_set_no_measures/")

    # map_fn = []

    # if mode == "risk":
    #     # check for netcdf
    #     for file in os.listdir(str(map_path)):
    #         if file.endswith("_maps.nc"):
    #             map_fn.append(map_path.joinpath(file))
    #     risk_output = True
    #     var = "risk_map"

    # elif mode == "single":
    #     map_fn.append(map_path.joinpath("sfincs_map.nc"))
    #     risk_output = False
    #     var = "zsmax"

    # configuration = {
    #     "setup_hazard": {
    #         "map_fn":   map_fn,                                                     # absolute or relative (with respect to the configuration.ini) path to the hazard file
    #         "map_type": "water_depth",                                              # description of the hazard file type
    #         "rp":       None,            				                              # hazard return period in years, required for a risk calculation (optional)
    #         "crs":      None,  						                              # coordinate reference system of the hazard file (optional)
    #         "nodata":   -999,             	                                      # value that is assigned as nodata (optional)
    #         "var":      var,							                              # hazard variable name in NetCDF input files (optional)
    #         "chunks":   "auto",  						                              # chunk sizes along each dimension used to load the hazard file into a dask array (default is 'auto') (optional)
    #         "name_catalog": None,
    #         "risk_output":  risk_output,
    #     }
    # }