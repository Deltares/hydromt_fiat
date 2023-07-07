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

@pytest.mark.parametrize("case", list(_cases.keys()))
def test_hazard(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    if root.exists:
        shutil.rmtree(root)

    # configuration = {
    #     "setup_hazard": {
    #         "map_fn":   ["C:/Users/fuentesm/CISNE/Deltares/Delft-FIAT/test/tmp/overland/sfincs_map.nc"], #, "C:/Users/fuentesm/CISNE/Deltares/Delft-FIAT/test/tmp/overland/sfincs_map.nc"],       # ["Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth","Current_prob_event_set_combined_doNothing_withSeaWall_RP=50_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=100_max_flood_depth"]                         #map_fn   = ["Current_prob_event_set_combined_doNothing_withSeaWall_RP=1_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=5_max_flood_depth"]					    		# absolute or relative (with respect to the configuration.ini) path to the hazard file
    #         "map_type": "water_depth",                                                             # description of the hazard file type
    #         "rp":       None,            				    	                              # hazard return period in years, required for a risk calculation (optional)
    #         "crs":      None,  						                              # coordinate reference system of the hazard file (optional)
    #         "nodata":   -99999,             				                                      # value that is assigned as nodata (optional)
    #         "var":      "zsmax",							                              # hazard variable name in NetCDF input files (optional)
    #         "chunks":   "auto",  						                              # chunk sizes along each dimension used to load the hazard file into a dask array (default is 'auto') (optional)
    #         "name_catalog": None,
    #         "risk_output": False,	
    #     }
    # }

    # configuration = {
    #     "setup_hazard": {   
    #         "map_fn":   ["P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=1_max_flood_depth.tif", "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth.tif"],       # ["Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth","Current_prob_event_set_combined_doNothing_withSeaWall_RP=50_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=100_max_flood_depth"]                         #map_fn   = ["Current_prob_event_set_combined_doNothing_withSeaWall_RP=1_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=5_max_flood_depth"]					    		# absolute or relative (with respect to the configuration.ini) path to the hazard file
    #         "map_type": "water_depth",                                                             # description of the hazard file type
    #         "rp":       None,            				    	                              # hazard return period in years, required for a risk calculation (optional)
    #         "crs":      None,  						                              # coordinate reference system of the hazard file (optional)
    #         "nodata":   -99999,             				                                      # value that is assigned as nodata (optional)
    #         "var":      None,							                              # hazard variable name in NetCDF input files (optional)
    #         "chunks":   "auto",  						                              # chunk sizes along each dimension used to load the hazard file into a dask array (default is 'auto') (optional)
    #         "name_catalog": "flood_maps",
    #         "risk_output": True,	
    #     }
    # }


    mode = "risk"
    map_path = Path("C:/Users/fuentesm/CISNE/Deltares/FloodAdapt/tests/test_database/charleston/output/simulations/current_test_set_no_measures/")
    # mode = "single"
    # map_path = Path("C:/Users/fuentesm/CISNE/Deltares/FloodAdapt/tests/test_database/charleston/output/simulations/current_extreme12ft_no_measures/overland")

    map_fn = []

    if mode == "risk":
        # check for netcdf
        for file in os.listdir(str(map_path)):
            if file.endswith("_maps.nc"):
                map_fn.append(map_path.joinpath(file))
        risk_output = True
        var = "risk_map"

    elif mode == "single":
        map_fn.append(map_path.joinpath("sfincs_map.nc"))
        risk_output = False
        var = "zsmax"


    configuration = {
        "setup_hazard": {   
            "map_fn":   map_fn, #["C:/Users/fuentesm/CISNE/Deltares/FloodAdapt/tests/test_database/charleston/output/simulations/current_test_set_no_measures/RP=1_maps.nc", "C:/Users/fuentesm/CISNE/Deltares/FloodAdapt/tests/test_database/charleston/output/simulations/current_test_set_no_measures/RP=2_maps.nc", "C:/Users/fuentesm/CISNE/Deltares/FloodAdapt/tests/test_database/charleston/output/simulations/current_test_set_no_measures/RP=5_maps.nc"],       # ["Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth","Current_prob_event_set_combined_doNothing_withSeaWall_RP=50_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=100_max_flood_depth"]                         #map_fn   = ["Current_prob_event_set_combined_doNothing_withSeaWall_RP=1_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=5_max_flood_depth"]					    		# absolute or relative (with respect to the configuration.ini) path to the hazard file
            "map_type": "water_depth",                                                             # description of the hazard file type
            "rp":       None,            				    	                              # hazard return period in years, required for a risk calculation (optional)
            "crs":      None,  						                              # coordinate reference system of the hazard file (optional)
            "nodata":   -999,             				                                      # value that is assigned as nodata (optional)
            "var":      var,							                              # hazard variable name in NetCDF input files (optional)
            "chunks":   "auto",  						                              # chunk sizes along each dimension used to load the hazard file into a dask array (default is 'auto') (optional)
            "name_catalog": None,
            "risk_output":  risk_output,	
        }
    }

    # configuration = {
    #     "setup_hazard": {   
    #         "map_fn":   ["C:/Users/fuentesm/CISNE/Deltares/FloodAdapt/tests/test_database/charleston/output/simulations/current_test_set_no_measures/RP=1_maps.nc", "C:/Users/fuentesm/CISNE/Deltares/FloodAdapt/tests/test_database/charleston/output/simulations/current_test_set_no_measures/RP=2_maps.nc", "C:/Users/fuentesm/CISNE/Deltares/FloodAdapt/tests/test_database/charleston/output/simulations/current_test_set_no_measures/RP=5_maps.nc"],       # ["Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth","Current_prob_event_set_combined_doNothing_withSeaWall_RP=50_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=100_max_flood_depth"]                         #map_fn   = ["Current_prob_event_set_combined_doNothing_withSeaWall_RP=1_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth", "Current_prob_event_set_combined_doNothing_withSeaWall_RP=5_max_flood_depth"]					    		# absolute or relative (with respect to the configuration.ini) path to the hazard file
    #         "map_type": "water_depth",                                                             # description of the hazard file type
    #         "rp":       None,            				    	                              # hazard return period in years, required for a risk calculation (optional)
    #         "crs":      None,  						                              # coordinate reference system of the hazard file (optional)
    #         "nodata":   -99999,             				                                      # value that is assigned as nodata (optional)
    #         "var":      "risk_maps",							                              # hazard variable name in NetCDF input files (optional)
    #         "chunks":   "auto",  						                              # chunk sizes along each dimension used to load the hazard file into a dask array (default is 'auto') (optional)
    #         "name_catalog": None,
    #         "risk_output": True,	
    #     }
    # }



    logger = setuplog("hydromt_fiat", log_level=10)
    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(root=root, mode="w", data_libs=[data_catalog_yml], logger=logger)
    region = fm.data_catalog.get_geodataframe("region", variables=None)
    opt = configread(_cases[case]["ini"])
    # fm.build(region={"geom": region}, opt=opt)
    fm.build(region={"geom": region}, opt=configuration)
    fm.write()
