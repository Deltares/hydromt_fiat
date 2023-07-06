from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest

EXAMPLEDIR = Path().absolute() / "local_test_database"
DATADIR = Path().absolute() / "hydromt_fiat" / "data"

_cases = {
    "Test_SVI": {
        "data_catalogue": DATADIR / "hydromt_fiat_catalog_USA.yml",
        "folder": "Test_SVI",
        "configuration": {
            "setup_social_vulnerability_index": {
                "census_key": "495a349ce22bdb1294b378fb199e4f27e57471a9",
                "codebook_fn": "social_vulnerability",
                "state_abbreviation": "SC",
                "blockgroup_fn": "blockgroup_shp_data",
            }
        },
    }
}


@pytest.mark.parametrize("case", list(_cases.keys()))
# @pytest.mark.skip(reason="Needs to be updated")
def test_SVI(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["folder"])
    logger = setuplog("hydromt_fiat", log_level=10)
    data_libs = EXAMPLEDIR.joinpath(_cases[case]["data_catalogue"])
    hyfm = FiatModel(root=root, mode="w", data_libs=data_libs, logger=logger)
    # config = configread(_cases[case]["configuration"])

    # Now we will add data from the user to the data catalog.
    to_add = {
        "blockgroup_shp_data": {
            "path": str(
                DATADIR
                / "social_vulnerability"
                / "test_blockgroup_shp"
                / "tl_2022_45_bg.shp"
            ),
            "data_type": "GeoDataFrame",
            "driver": "vector",
            "crs": 4326,
            "category": "social_vulnerability",
        }
    }

    hyfm.data_catalog.from_dict(to_add)
    hyfm.build(opt=_cases[case]["configuration"])

    assert hyfm
    print("hi")
