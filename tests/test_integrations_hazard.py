from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil

EXAMPLEDIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database"
)

_cases = {
    "integration_hazard": {
        "data_catalogue": EXAMPLEDIR / "fiat_catalog.yml",
        "dir": "test_hazard_v2",
        "configuration": {
            "setup_global_settings": {"crs": "epsg:4326"},
            "setup_output": {
                "output_dir": "output",
                "output_csv_name": "output.csv",
                "output_vector_name": "spatial.gpkg",
            },
            "setup_vulnerability": {
                "vulnerability_fn": "hazus_vulnerability_curves",
                "vulnerability_identifiers_and_linking_fn": ".\\examples\\data\\vulnerability_test_file_input.csv",
                "functions_mean": "default",
                "functions_max": ["AGR1"],
                "unit": "feet",
                "scale": 0.1,
            },
            "setup_exposure_vector": {
                "asset_locations": "NSI",
                "occupancy_type": "NSI",
                "max_potential_damage": "NSI",
                "ground_floor_height": 1,
                "ground_floor_height_unit": "ft",
            },
            "setup_hazard": {
                "map_fn": [
                    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=1_max_flood_depth.tif",
                    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=2_max_flood_depth.tif",
                    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=5_max_flood_depth.tif",
                    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=10_max_flood_depth.tif",
                    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=25_max_flood_depth.tif",
                    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=50_max_flood_depth.tif",
                    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=100_max_flood_depth.tif",
                ],
                "map_type": "water_depth",  # description of the hazard file type
                "rp": None,  # hazard return period in years, required for a risk calculation (optional)
                "crs": None,  # coordinate reference system of the hazard file (optional)
                "nodata": -99999,  # value that is assigned as nodata (optional)
                "var": None,  # hazard variable name in NetCDF input files (optional)
                "chunks": "auto",  # chunk sizes along each dimension used to load the hazard file into a dask array (default is 'auto') (optional)
                "name_catalog": "flood_maps",
                "risk_output": True,
            },
        },
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_hazard(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    if root.exists:
        shutil.rmtree(root)

    logger = setuplog("hydromt_fiat", log_level=10)
    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(root=root, mode="w", data_libs=[data_catalog_yml], logger=logger)
    region = fm.data_catalog.get_geodataframe("region", variables=None)
    fm.build(region={"geom": region}, opt=_cases[case]["configuration"])
    fm.write()
