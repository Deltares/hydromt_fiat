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

#set pyogrio as default engine
gpd.options.io_engine = "pyogrio"

#Load Data
EXAMPLEDIR = Path(
    r"n:\Deltabox\Postbox\Rautenbach, Sarah\FIAT_model"
)

_cases = {
    "read": {
               "dir": "test_aggregation_area",
    },
}

#Set up Fiat Model

@pytest.mark.parametrize("case", list(_cases.keys()))
def test_aggregation_areas(case: ParameterSet | Sequence[object] | object):
    # Read model in examples folder.
    root = EXAMPLEDIR
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", logger=logger)
    fm.read()

    #Here comes the code
    filepath = Path(r"N:\Deltabox\Postbox\Rautenbach, Sarah\FIAT_model\Base_Zoning.geojson")
    exposure_gdf = fm.exposure.get_full_gdf(fm.exposure.exposure_db)
    aggregation_attribute = 'ZONE_BASE'
    new_exposure = join_exposure_aggregation_area(exposure_gdf,filepath,aggregation_attribute)
    
   #Safe file
    new_exposure.to_file(r"N:\Deltabox\Postbox\Rautenbach, Sarah\FIAT_model\new_exposure_test1.shp") 






    # Check if the exposure object exists
    assert isinstance(fm.exposure, ExposureVector)

    # Check if the exposure database exists
    assert not fm.exposure.exposure_db.empty

    # Check if the vulnerability object exists
    assert isinstance(fm.vulnerability, Vulnerability)

    # Check if the vulnerability functions exist
    assert len(fm.vulnerability.functions) > 0