from pathlib import Path

import geopandas as gpd
import pytest
import xarray as xr

from hydromt_fiat import FIATModel
from hydromt_fiat.components import (
    ConfigComponent,
    ExposureGeomsComponent,
    ExposureGridComponent,
    HazardComponent,
    VulnerabilityComponent,
)


def test_model_empty(tmp_path: Path):
    # Setup an empty fiat model
    model = FIATModel(tmp_path)

    # Assert some basic statements
    assert "config" in model.components
    assert "region" in model.components
    assert model.region is None
    assert len(model.components) == 6


def test_model_basic_read_write(tmp_path: Path):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")

    # Call the necessary setup methods
    model.setup_config(some_var="some_value")
    # Write the model
    model.write()
    model = None
    assert Path(tmp_path, "settings.toml").is_file()

    # Model in read mode
    model = FIATModel(tmp_path, mode="r")
    model.read()

    assert len(model.config.data) != 0


def test_model_clip(  # Dont like this to much, as it is a bit of an integration test
    tmp_path: Path,
    build_region: gpd.GeoDataFrame,
    build_region_small: gpd.GeoDataFrame,
    exposure_vector: gpd.GeoDataFrame,
    exposure_grid: xr.Dataset,
    hazard: xr.Dataset,
):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")

    # Set data like a dummy
    model.components["region"]._data = {"region": build_region}
    model.exposure_geoms._data = {"foo": exposure_vector}
    model.exposure_grid._data = exposure_grid
    model.hazard._data = hazard
    # Assert the current state
    assert build_region_small.crs.to_epsg() == 28992
    assert model.exposure_geoms.data["foo"].shape[0] == 543
    assert model.exposure_grid.data.commercial_content.shape == (67, 50)
    assert model.hazard.data.flood_event.shape == (34, 25)

    # Call the clip function
    model.clip(region=build_region_small)
    # Assert the state after
    assert model.region.crs.to_epsg() == 4326
    assert model.exposure_geoms.data["foo"].shape[0] == 12
    assert model.exposure_grid.data.commercial_content.shape == (11, 12)
    assert model.hazard.data.flood_event.shape == (7, 6)


def test_model_setup_config(tmp_path: Path):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")

    # Setup some config variables
    model.setup_config(
        **{
            "global.model": "geom",
            "global.srs.value": "EPSG:4326",
            "output.path": "output",
        }
    )

    # Assert the config component
    assert model.config.data["output"] == {"path": "output"}
    assert model.config.get("output.path") == "output"
    assert len(model.config.get("global")) == 2
    assert model.config.get("global.srs") == {"value": "EPSG:4326"}


def test_model_setup_region(tmp_path: Path, build_region_path: Path):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")
    assert model.region is None

    # Setup the region
    model.setup_region(region=build_region_path)
    assert model.region is not None
    assert isinstance(model.region, gpd.GeoDataFrame)
    assert len(model.region) == 1


def test_model_setup_region_from_gdf(tmp_path: Path, build_region: gpd.GeoDataFrame):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")
    assert model.region is None

    # Setup the region
    model.setup_region(region=build_region)
    assert model.region is not None
    assert isinstance(model.region, gpd.GeoDataFrame)
    assert len(model.region) == 1


def test_model_setup_region_error(tmp_path: Path):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")

    # Setup the region pointing to not a file
    region_no = Path(tmp_path, "region.geojson")
    with pytest.raises(FileNotFoundError, match=region_no.as_posix()):
        model.setup_region(region=region_no)

    # Setup the region with the wrong type of input
    with pytest.raises(
        TypeError,
        match="Region should either be of type `gpd.GeoDataframe` or `Path`/ `str`",
    ):
        model.setup_region(region=2)


def test_model_properties(model_with_region: FIATModel):
    # Setup an empty fiat model
    model = model_with_region

    # Assert the types of model properties
    assert isinstance(model.config, ConfigComponent)
    assert isinstance(model.exposure_geoms, ExposureGeomsComponent)
    assert isinstance(model.exposure_grid, ExposureGridComponent)
    assert isinstance(model.hazard, HazardComponent)
    assert isinstance(model.region, gpd.GeoDataFrame)
    assert isinstance(model.vulnerability, VulnerabilityComponent)
