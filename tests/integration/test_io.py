from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest

from hydromt_fiat import FIATModel
from hydromt_fiat.utils import (
    CURVES,
    EXPOSURE,
    EXPOSURE_GRID_SETTINGS,
    GEOM,
    HAZARD,
    MODEL_TYPE,
    REGION,
    SETTINGS,
    VAR_AS_BAND,
    VULNERABILITY,
)
from tests.conftest import HAS_INTERNET, HAS_LOCAL_DATA


@pytest.mark.skipif(
    not HAS_INTERNET and not HAS_LOCAL_DATA,
    reason="No internet or local data cache available",
)
@pytest.mark.integration
def test_model_io(tmp_path: Path, model_data_clipped_path: Path):
    # Create the model to read
    model = FIATModel(root=model_data_clipped_path)

    # Read the model
    model.read()

    # Assert its state
    assert len(model.config.data) == 4
    assert model.config.get(MODEL_TYPE) == GEOM
    assert isinstance(model.region, gpd.GeoDataFrame)
    np.testing.assert_almost_equal(model.region.total_bounds[0], 85675, decimal=0)
    assert len(model.exposure_geoms.data) == 1
    # Even thought the model type is geom, it will read it from it's default path
    assert "buildings" in model.exposure_geoms.data
    assert len(model.exposure_grid.data.data_vars) == 4
    assert "industrial_content" in model.exposure_grid.data
    assert len(model.hazard.data.data_vars) == 1
    assert "flood_event" in model.hazard.data
    assert not model.vulnerability.data.curves.empty
    assert not model.vulnerability.data.identifiers.empty

    # Set the root to a new location and in write mode
    model.root.set(path=tmp_path, mode="w")

    # Write the model to that location
    model.write()

    # Assert the output
    assert Path(tmp_path, f"{SETTINGS}.toml").is_file()
    assert Path(tmp_path, f"{REGION}.geojson").is_file()
    assert Path(tmp_path, EXPOSURE, "buildings.fgb").is_file()
    assert Path(tmp_path, EXPOSURE, "spatial.nc").is_file()
    assert Path(tmp_path, f"{HAZARD}.nc").is_file()
    assert Path(tmp_path, VULNERABILITY, f"{CURVES}.csv").is_file()
    assert Path(tmp_path, VULNERABILITY, f"{CURVES}_id.csv").is_file()
    # Assert the addition of some settings set during I/O
    assert model.config.get(f"{EXPOSURE_GRID_SETTINGS}.{VAR_AS_BAND}")
