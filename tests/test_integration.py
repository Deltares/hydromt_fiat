from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil
import geopandas as gpd

EXAMPLEDIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database"
)
DATADIR = Path().absolute() / "hydromt_fiat" / "data"

_region = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "coordinates": [
                    [
                        [-79.92169686568795, 32.768208904171374],
                        [-79.92169686568795, 32.77745096033627],
                        [-79.94881762529997, 32.77745096033627],
                        [-79.94881762529997, 32.768208904171374],
                        [-79.92169686568795, 32.768208904171374],
                    ]
                ],
                "type": "Polygon",
            },
        }
    ],
}

_cases = {
    "integration_hazard_event_charleston": {
        "data_catalogue": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "dir": "test_hazard_event_charleston",
        "configuration": {
            "setup_global_settings": {"crs": "epsg:4326"},
            "setup_output": {
                "output_dir": "output",
                "output_csv_name": "output.csv",
                "output_vector_name": "spatial.gpkg",
            },
            "setup_vulnerability": {
                "vulnerability_fn": "default_vulnerability_curves",
                "vulnerability_identifiers_and_linking_fn": "default_hazus_iwr_linking",
                "functions_mean": "default",
                "functions_max": ["AGR1"],
                "unit": "feet",
                "step_size": 0.01,
            },
            "setup_exposure_buildings": {
                "asset_locations": "NSI",
                "occupancy_type": "NSI",
                "max_potential_damage": "NSI",
                "ground_floor_height": "NSI",
                "unit": "feet",
            },
            "setup_hazard": {
                "map_fn": [
                    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/data/Hazard/Current_prob_event_set_combined_doNothing_withSeaWall_RP=100_max_flood_depth.tif",
                ],
                "map_type": "water_depth",  # description of the hazard file type
                "rp": None,  # hazard return period in years, required for a risk calculation (optional)
                "crs": "EPSG:4326",  # coordinate reference system of the hazard file (optional)
                "nodata": -99999,  # value that is assigned as nodata (optional)
                "var": None,  # hazard variable name in NetCDF input files (optional)
                "chunks": "auto",  # chunk sizes along each dimension used to load the hazard file into a dask array (default is 'auto') (optional)
                "risk_output": False,
            },
        },
        "region": _region,
    },
    "integration_hazard_risk_charleston": {
        "data_catalogue": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "dir": "test_hazard_risk_charleston",
        "configuration": {
            "setup_global_settings": {"crs": "epsg:4326"},
            "setup_output": {
                "output_dir": "output",
                "output_csv_name": "output.csv",
                "output_vector_name": "spatial.gpkg",
            },
            "setup_vulnerability": {
                "vulnerability_fn": "default_vulnerability_curves",
                "vulnerability_identifiers_and_linking_fn": "default_hazus_iwr_linking",
                "functions_mean": "default",
                "functions_max": ["AGR1"],
                "unit": "feet",
                "step_size": 0.01,
            },
            "setup_exposure_buildings": {
                "asset_locations": "NSI",
                "occupancy_type": "NSI",
                "max_potential_damage": "NSI",
                "ground_floor_height": "NSI",
                "unit": "feet",
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
                "rp": [
                    1,
                    2,
                    5,
                    10,
                    25,
                    50,
                    100,
                ],  # hazard return period in years, required for a risk calculation (optional)
                "crs": "EPSG:4326",  # coordinate reference system of the hazard file (optional)
                "nodata": -99999,  # value that is assigned as nodata (optional)
                "var": None,  # hazard variable name in NetCDF input files (optional)
                "chunks": "auto",  # chunk sizes along each dimension used to load the hazard file into a dask array (default is 'auto') (optional)
                "risk_output": True,
            },
        },
        "region": _region,
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_integration(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    if root.exists():
        shutil.rmtree(root)

    logger = setuplog("hydromt_fiat", log_level=10)
    data_catalog_yml = str(_cases[case]["data_catalogue"])

    fm = FiatModel(root=root, mode="w", data_libs=[data_catalog_yml], logger=logger)
    region = gpd.GeoDataFrame.from_features(_cases[case]["region"], crs=4326)
    fm.build(region={"geom": region}, opt=_cases[case]["configuration"])
    fm.write()

    # Check if the exposure data exists
    assert root.joinpath("exposure", "buildings.gpkg").exists()
    assert root.joinpath("exposure", "exposure.csv").exists()
    assert root.joinpath("geoms", "region.geojson").exists()

    # Check if the vulnerability data exists
    assert root.joinpath("vulnerability", "vulnerability_curves.csv").exists()

    # Check if the hazard folder exists
    assert root.joinpath("hazard").exists()

    # Check if the output data folder exists
    assert root.joinpath("output").exists()