from typing import Sequence
from _pytest.mark.structures import ParameterSet
from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import geopandas as gpd
import pandas as pd
from hydromt_fiat.workflows.building_footprints import join_exposure_building_footprint
from hydromt_fiat.workflows.building_footprints import join_exposure_bf
from hydromt_fiat.workflows.exposure_vector import ExposureVector
from hydromt_fiat.workflows.vulnerability import Vulnerability
import shutil

# set pyogrio as default engine
gpd.options.io_engine = "pyogrio"

#Datasource: https://github.com/microsoft/USBuildingFootprints
EXAMPLEDIR = Path(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\HydroMT\Issue_Solving\#133\testcase_data")

#Create test
_cases = {
    "bf_test_1": {
        "new_root": Path(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\HydroMT\Issue_Solving\#133\output"),
        "configuration": {
            "setup_building_footprint": {
                "building_footprint_fn": Path(r"C:\Users\rautenba\OneDrive - Stichting Deltares\Documents\Projects\HydroMT\Issue_Solving\#133\testcase_data\building_footprints\building_footprint.gpkg"),
                "attribute_name": "B_footprint",
                }
        },
    }
}

# Set up Fiat Model
@pytest.mark.parametrize("case", list(_cases.keys()))
def test_building_footprints(case: ParameterSet | Sequence[object] | object):
    # Read model in examples folder.
    root = EXAMPLEDIR
    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", logger=logger)
    fm.read()

    fm.build(write=False, opt=_cases[case]["configuration"])
    fm.set_root(_cases[case]["new_root"])
    fm.write()