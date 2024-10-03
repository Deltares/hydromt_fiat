from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil
import geopandas as gpd

EXAMPLEDIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database"
)

_region = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "coordinates": [
                    [
                        [171.090746817905512, 7.121358418747697],
                        [171.217560473873988, 7.123661889257901],
                        [171.217560473873988, 7.123661889257901],
                        [171.216525686221701, 7.063008661686558],
                        [171.092077237014792, 7.063384936479417],
                        [171.090746817905512, 7.121358418747697],
                    ]
                ],
                "type": "Polygon",
            },
        }
    ],
}

_region_charleston = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "coordinates": [
                    [
                        [-80.028357024435763, 32.84613574478697],
                        [-79.863521617196227, 32.833781113480647],
                        [-79.854779619756741, 32.734963735677987],
                        [-80.026105579065501, 32.739367988104483],
                        [-80.028357024435763, 32.84613574478697],
                    ]
                ],
                "type": "Polygon",
            },
        }
    ],
}


_cases = {
    "event_map": {
        "region": _region_charleston,
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
        },
    },
    "risk_map": {
        "region": _region_charleston,
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
        },
    },
    "event_map_geotiffs": {
        "region": _region,
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
        },
    },
    "risk_map_geotiffs": {
        "region": _region,
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
        },
    },
    "event_map_geotiff2": {
        "region": _region_charleston,
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
        },
    },
    "risk_map_geotiff2": {
        "region": _region_charleston,
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
        },
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_hazard(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    if root.exists():
        shutil.rmtree(root)

    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="w", logger=logger)
    region = gpd.GeoDataFrame.from_features(_cases[case]["region"], crs=4326)

    fm.build(region={"geom": region}, opt=_cases[case]["configuration"])
    fm.write()

    # Check if the hazard folder exists
    assert root.joinpath("hazard").exists()
