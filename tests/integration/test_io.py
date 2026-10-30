from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest

from hydromt_fiat import FIATModel
from hydromt_fiat.utils import (
    CURVES,
    EXPOSURE,
    GEOM,
    HAZARD,
    REGION,
    SETTINGS,
)


@pytest.mark.integration
def test_model_io(tmp_path: Path, model_data_clipped_path: Path):
    # Create the model to read
    model = FIATModel(root=model_data_clipped_path, config_fname="settings_geom.toml")

    # Read the model
    model.read()

    # Assert its state
    assert model.config.data.type == GEOM
    assert isinstance(model.region, gpd.GeoDataFrame)
    np.testing.assert_almost_equal(model.region.total_bounds[0], 85675, decimal=0)
    assert len(model.exposure_geoms.data) == 1
    # Even thought the model type is geom, it will read it from it's default path
    assert "buildings" in model.exposure_geoms.data
    assert len(model.hazard.data.data_vars) == 1
    assert "flood_event" in model.hazard.data
    assert len(model.vulnerability.data.curves) != 0
    assert len(model.vulnerability.data.identifiers) != 0

    # Set the root to a new location and in write mode
    model.root.set(path=tmp_path, mode="w")

    # Write the model to that location
    model.write()

    # Assert the output
    assert Path(tmp_path, f"{SETTINGS}_geom.toml").is_file()
    assert Path(tmp_path, f"{REGION}.geojson").is_file()
    assert Path(tmp_path, EXPOSURE, "buildings.fgb").is_file()
    assert Path(tmp_path, f"{HAZARD}.nc").is_file()
    assert Path(tmp_path, f"{CURVES}.nc").is_file()
    assert Path(tmp_path, f"{CURVES}_id.nc").is_file()
