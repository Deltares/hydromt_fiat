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
                        [-80.0808, 32.7005],
                        [-79.8756, 32.8561],
                        [-79.8756, 32.7005],
                        [-80.0808, 32.8561],
                        [-80.0808, 32.7005],
                    ]
                ],
                "type": "Polygon",
            },
        }
    ],
}

_cases = {
    "Test_equity_data": {
        "data_catalogue": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "folder": "Test_equity_data",
        "region": _region,
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
            },
            "setup_exposure_buildings": {
                "asset_locations": "NSI",
                "occupancy_type": "NSI",
                "max_potential_damage": "NSI",
                "ground_floor_height": "NSI",
                "unit": "feet",
            },
            "setup_equity_data": {
                "census_key": "495a349ce22bdb1294b378fb199e4f27e57471a9",
                "year_data": 2021,
            },
        },
    }
}


@pytest.mark.parametrize("case", list(_cases.keys()))
# @pytest.mark.skip(reason="Needs to be updated")
def test_equity_data(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["folder"])
    if root.exists():
        shutil.rmtree(root)
    logger = setuplog("hydromt_fiat", log_level=10)
    data_libs = EXAMPLEDIR.joinpath(_cases[case]["data_catalogue"])
    fm = FiatModel(root=root, mode="w", data_libs=data_libs, logger=logger)

    region = gpd.GeoDataFrame.from_features(_cases[case]["region"], crs=4326)
    fm.build(region={"geom": region}, opt=_cases[case]["configuration"])
    fm.write()

    # Check if the exposure data exists
    assert root.joinpath("exposure", "buildings.gpkg").exists()
    assert root.joinpath("exposure", "exposure.csv").exists()
    assert root.joinpath("geoms", "region.geojson").exists()

    # Check if the equity data exists
    assert root.joinpath("exposure", "equity", "equity_data.csv").exists()

    # Check if the vulnerability data exists
    assert root.joinpath("vulnerability", "vulnerability_curves.csv").exists()
