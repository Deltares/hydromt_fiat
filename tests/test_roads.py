from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil
import geopandas as gpd
import pandas as pd


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
    "roads_from_OSM": {
        "data_catalogue": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "dir": "test_roads_from_OSM",
        "configuration": {
            "setup_road_vulnerability": {
                "vertical_unit": "feet",
                "threshold_value": 0.5,
                "min_hazard_value": 0,
                "max_hazard_value": 15,
                "step_hazard_value": 1,
            },
            "setup_exposure_roads": {
                "roads_fn": "OSM",
                "road_types": ["motorway", "primary", "secondary", "tertiary"],
                "road_damage": "default_road_max_potential_damages",
                "unit": "feet",
            },
        },
        "region": _region,
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_setup_roads(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    if root.exists():
        shutil.rmtree(root)
    data_catalog_yml = str(_cases[case]["data_catalogue"])

    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="w", data_libs=[data_catalog_yml], logger=logger)

    region = gpd.GeoDataFrame.from_features(_cases[case]["region"], crs=4326)
    fm.build(region={"geom": region}, opt=_cases[case]["configuration"])
    fm.write()

    # Check if the exposure data exists
    assert root.joinpath("exposure", "roads.gpkg").exists()
    assert root.joinpath("exposure", "exposure.csv").exists()
    assert root.joinpath("geoms", "region.geojson").exists()

    # Read the resulting exposure data and check if the required columns exist
    exposure = pd.read_csv(root.joinpath("exposure", "exposure.csv"))
    required_columns = [
        "secondary_object_type",
        "object_name",
        "lanes",
        "object_id",
        "primary_object_type",
        "extract_method",
        "ground_flht",
        "max_damage_structure",
        "segment_length",
    ]
    assert set(required_columns) == set(exposure.columns)

    # Check if the vulnerability data exists
    assert root.joinpath("vulnerability", "vulnerability_curves.csv").exists()

    # Check if the hazard folder exists
    assert root.joinpath("hazard").exists()

    # Check if the output data folder exists
    assert root.joinpath("output").exists()

    # Check if the output gives the correct solution
    assert fm.vulnerability.functions == {
        "roads": [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    }
    assert fm.vulnerability.hazard_values == [
        0.0,
        0.49,
        0.5,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
    ]
