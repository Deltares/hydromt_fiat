from pathlib import Path

from hydromt_fiat.settings import (
    DEFAULT_GEOM_SETTINGS,
    GeomSettings,
    GridSettings,
    load_settings,
)
from hydromt_fiat.utils import GEOM, GRID


def test_settings():
    # Just create an instance
    s = GeomSettings()

    # Assert some default values
    assert s.type == GEOM
    assert s.threads == 1
    assert s.risk == False

    # Assert the file
    assert s.exposure is None
    assert s.hazard is None
    assert s.vulnerability is None

    # Assert it's equal to the default
    assert s == DEFAULT_GEOM_SETTINGS


def test_load_settings_geom(model_data_clipped_path: Path):
    # Call the function with a string path
    s = load_settings(str(Path(model_data_clipped_path, "settings_geom.toml")))

    # Assert the state
    assert isinstance(s, GeomSettings)
    assert s.type == GEOM
    assert s.hazard.variables[0].name == "flood_event"
    assert s.vulnerability.variables[0].name == "default"
    assert s.exposure[0].vulnerability == "default"
    # Assert the paths are relative to the settings file
    assert s.hazard.file == Path(model_data_clipped_path, "hazard.nc")


def test_load_settings_grid(model_data_clipped_path: Path):
    # Call the function
    s = load_settings(Path(model_data_clipped_path, "settings_grid.toml"))

    # Assert the state
    assert isinstance(s, GridSettings)
    assert s.type == GRID
    assert len(s.exposure.variables) == 7
