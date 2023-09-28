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
    "integration": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_hazard",
        "ini": EXAMPLEDIR / "test_hazard_unique.ini",
    },
}


@pytest.mark.skip(reason="Hazard functions not yet finalized")
@pytest.mark.parametrize("case", list(_cases.keys()))
def test_hazard(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    if root.exists:
        shutil.rmtree(root)

    # uncomment to test event analysis from geotiff file
    configuration = {
        "setup_hazard": {
            "map_fn": [
                "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=1_max_flood_depth.tif"
            ],
            "map_type": "water_depth",
            "rp": None,
            "crs": None,
            "nodata": -99999,
            "var": None,
            "chunks": "auto",
            "name_catalog": None,
            "risk_output": False,
        }
    }

    # uncomment to test risk analysis from geotiff file
    # configuration = {
    #     "setup_hazard": {
    #         "map_fn":   ["P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=1_max_flood_depth.tif", "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth.tif", "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=5_max_flood_depth.tif"],
    #         "map_type": "water_depth",
    #         "rp":       None,
    #         "crs":      None,
    #         "nodata":   -99999,
    #         "var":      None,
    #         "chunks":   "auto",
    #         "name_catalog": None,
    #         "risk_output": True,
    #     }
    # }

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

    logger = setuplog("hydromt_fiat", log_level=10)
    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(root=root, mode="w", data_libs=[data_catalog_yml], logger=logger)
    region = fm.data_catalog.get_geodataframe("region", variables=None)
    # opt = configread(_cases[case]["ini"])
    # fm.build(region={"geom": region}, opt=opt)
    fm.build(region={"geom": region}, opt=configuration)
    fm.write()

    # Check if the hazard folder exists
    assert root.joinpath("hazard").exists()
