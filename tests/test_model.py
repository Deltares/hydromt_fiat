from pathlib import Path

import geopandas as gpd
import pytest

from hydromt_fiat import FIATModel


def test_empty_model(tmp_path: Path):
    # Setup an empty fiat model
    model = FIATModel(tmp_path)

    # Assert some basic statements
    assert "config" in model.components
    assert "region" in model.components
    assert model.region is None
    assert len(model.components) == 7


def test_basic_read_write(tmp_path: Path):
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


def test_setup_config(tmp_path: Path):
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
    assert model.config.get_value("output.path") == "output"
    assert len(model.config.get_value("global")) == 2
    assert model.config.get_value("global.srs") == {"value": "EPSG:4326"}


def test_setup_region(tmp_path: Path, build_region: Path):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")
    assert model.region is None

    # Setup the region
    model.setup_region(region=build_region)
    assert model.region is not None
    assert isinstance(model.region, gpd.GeoDataFrame)
    assert len(model.region) == 1


def test_setup_region_error(tmp_path: Path):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")

    # Setup the region
    region_no = Path(tmp_path, "region.geojson")
    with pytest.raises(FileNotFoundError, match=region_no.as_posix()):
        model.setup_region(region=region_no)


## Bloody integration tests
# TODO fill these in when the functionality is fully there
def test_fiatmodel_geom():
    pass


def test_fiatmodel_grid():
    pass
