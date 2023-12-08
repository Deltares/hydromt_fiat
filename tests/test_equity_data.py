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

_cases = {
    "Test_equity_data": {
        "data_catalogue": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "folder": "Test_equity_data",
        "configuration": {
            "setup_global_settings": {"crs": "epsg:4326"},
            "setup_output": {
                "output_dir": "output",
                "output_csv_name": "output.csv",
                "output_vector_name": "spatial.gpkg",
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

    fm.build(opt=_cases[case]["configuration"])
    fm.write()

    # Check if the exposure data exists
    assert root.joinpath("exposure", "buildings.gpkg").exists()
    assert root.joinpath("exposure", "exposure.csv").exists()
    assert root.joinpath("exposure", "region.gpkg").exists()

    # Check if the equity data exists
    assert root.joinpath("exposure", "equity", "equity_data.csv").exists()

    # Check if the vulnerability data exists
    assert root.joinpath("vulnerability", "vulnerability_curves.csv").exists()