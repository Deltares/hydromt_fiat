import tomllib
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import xarray as xr

from hydromt_fiat.writers import write_config, write_csv, write_geoms, write_grid


def test_write_config(tmp_path: Path, config_dummy: dict[str, Any]):
    config_dummy["baz"]["file1"] = "tmp.txt"
    p = Path(tmp_path, "settings.toml")
    # Call the functions
    write_config(data=config_dummy, write_path=p)

    # Assert the file is there
    assert p.is_file()
    # Read back in and assert
    with open(p, "r") as reader:
        data = tomllib.loads(reader.read())
    assert "foo" in data
    assert data == config_dummy


def test_write_csv(tmp_path: Path, vulnerability_curves: pd.DataFrame):
    p = Path(tmp_path, "foo.csv")
    # Call the functions
    write_csv(data=vulnerability_curves, write_path=p)

    # Assert the file
    assert p.is_file()
    # Assert it is readable by pandas
    assert pd.read_csv(p) is not None


def test_write_geoms(tmp_path: Path, exposure_vector_clipped: gpd.GeoDataFrame):
    p = Path(tmp_path, "foo.fgb")
    # Call the functions
    write_geoms(data=exposure_vector_clipped, write_path=p)

    # Assert the file
    assert p.is_file()
    # Assert it is readable by geopandas
    assert gpd.read_file(p) is not None


def test_write_grid(tmp_path: Path, hazard_clipped: xr.Dataset):
    p = Path(tmp_path, "foo.nc")
    # Call the functions
    write_grid(data=hazard_clipped, write_path=p)

    # Assert the file
    assert p.is_file()
    # Assert it is readable by xarray
    assert xr.open_dataset(p) is not None
