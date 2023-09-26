from typing import Sequence
from _pytest.mark.structures import ParameterSet
from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import geopandas as gpd
import pandas as pd
from hydromt_fiat.workflows.aggregation_areas import join_exposure_aggregation_area

from hydromt_fiat.workflows.exposure_vector import ExposureVector
from hydromt_fiat.workflows.vulnerability import Vulnerability

# set pyogrio as default engine
gpd.options.io_engine = "pyogrio"

# Load Data
EXAMPLEDIR = Path(r"n:\Deltabox\Postbox\Rautenbach, Sarah\FIAT_model")
# Remove after
my_dic = {
    "aggregation_area_fn": [
        r"N:\Deltabox\Postbox\Rautenbach, Sarah\FIAT_model\zones.gpkg",
        r"N:\Deltabox\Postbox\Rautenbach, Sarah\FIAT_model\zones2.gpkg",
    ]
}


_cases = {
    "aggregation_test_1": {
        "new_root": r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FIAT\modelbuilder_sprint",
        "configuration": {
            "setup_aggregation_areas": {
                "aggregation_area_fn": r"N:\Deltabox\Postbox\Rautenbach, Sarah\FIAT_model\zones.gpkg",
                "attribute_names": "ZONE_BASE",
                "label_names": "Zoning_map",
            }
        },
    },
    "aggregation_test_2": {
        "new_root": r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\FIAT\modelbuilder_sprint2",
        "configuration": {
            "setup_aggregation_areas_multiple": {
                "aggregation_area_fn": [
                    r"N:\Deltabox\Postbox\Rautenbach, Sarah\FIAT_model\zones.gpkg",
                    r"N:\Deltabox\Postbox\Rautenbach, Sarah\FIAT_model\zones2.gpkg",
                ],
                "attribute_names": ["ZONE_BASE", "LAND_USE"],
                "label_names": ["Zoning_map", "Land_use_map"],
            }
        },
    },
}


# Set up Fiat Model


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_aggregation_areas(case: ParameterSet | Sequence[object] | object):
    # Read model in examples folder.
    root = EXAMPLEDIR
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
