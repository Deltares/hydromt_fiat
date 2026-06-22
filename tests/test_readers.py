from pathlib import Path

import geopandas as gpd
import pandas as pd
import xarray as xr

from hydromt_fiat.readers import read_config, read_csv, read_geoms, read_grid


def test_read_config(model_data_clipped_path: Path):
    # Call the function
    o = read_config(Path(model_data_clipped_path, "settings.toml"))

    # Assert output
    assert isinstance(o, dict)
    assert o.get("exposure") is not None


def test_read_csv(model_data_clipped_path: Path):
    # Call the function
    o = read_csv(Path(model_data_clipped_path, "vulnerability", "curves.csv"))

    # Assert output
    assert isinstance(o, pd.DataFrame)
    assert "rs1" in o.columns


def test_read_geoms(model_data_clipped_path: Path):
    # Call the function
    o = read_geoms(Path(model_data_clipped_path, "exposure", "buildings.fgb"))

    # Assert output
    assert isinstance(o, gpd.GeoDataFrame)
    assert "fn_damage_structure" in o.columns


def test_read_geoms_split(exposure_vector_clipped_split_path: Path):
    # Call the function
    o = read_geoms(exposure_vector_clipped_split_path)

    # Assert output
    assert isinstance(o, gpd.GeoDataFrame)
    assert "fn_damage_structure" in o.columns


def test_read_grid(model_data_clipped_path: Path):
    # Call the function
    o = read_grid(Path(model_data_clipped_path, "hazard.nc"))

    # Assert the output
    assert isinstance(o, xr.Dataset)
    assert "flood_event" in o.data_vars
