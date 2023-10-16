import shutil
from pathlib import Path
from typing import Sequence

import pytest
from _pytest.mark.structures import ParameterSet
from hydromt.log import setuplog

from hydromt_fiat.fiat import FiatModel
from hydromt_fiat.workflows.exposure_vector import ExposureVector
from hydromt_fiat.workflows.vulnerability import Vulnerability

# Load Data
EXAMPLEDIR = Path().resolve() / "examples" / "data" / "aggregation_zones_example"

_cases = {
    "aggregation_test_1": {
        "new_root": EXAMPLEDIR / "aggregation_test_1_output",
        "configuration": {
            "setup_aggregation_areas": {
                "aggregation_area_fn": EXAMPLEDIR / "aggregation_zones" / "base_zones.gpkg",
                "attribute_names": "ZONE_BASE",
                "label_names": "Zoning_map",
            }
        },
    },
    "aggregation_test_2": {
        "new_root": EXAMPLEDIR / "aggregation_test_2_output",
        "configuration": {
            "setup_aggregation_areas": {
                "aggregation_area_fn": [
                    EXAMPLEDIR / "aggregation_zones" / "base_zones.gpkg",
                    EXAMPLEDIR / "aggregation_zones" / "land_use.gpkg",
                    EXAMPLEDIR / "aggregation_zones" / "accomodation_type.gpkg",
                ],
                "attribute_names": ["ZONE_BASE", "LAND_USE","ACCOM"],
                "label_names": ["Zoning_map", "Land_use_map","Accomodation_Zone"],
            }
        },
    },
}



# Set up Fiat Model
@pytest.mark.parametrize("case", list(_cases.keys()))
def test_aggregation_areas(case: ParameterSet | Sequence[object] | object):
    # Read model in examples folder.
    root = EXAMPLEDIR / "fiat_model"
    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", logger=logger)
    fm.read()

    fm.build(write=False, opt=_cases[case]["configuration"])
    fm.set_root(_cases[case]["new_root"])
    fm.write()

    # Check if the exposure object exists
    assert isinstance(fm.exposure, ExposureVector)

    # Check if the exposure database exists
    assert not fm.exposure.exposure_db.empty

    # Check if the vulnerability object exists
    assert isinstance(fm.vulnerability, Vulnerability)

    # Check if the vulnerability functions exist
    assert len(fm.vulnerability.functions) > 0
