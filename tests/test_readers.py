from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from hydromt_fiat.readers import read_config, read_csv, read_geoms, read_grid
from hydromt_fiat.writers import write_grid


def test_read_config(model_data_clipped_path: Path):
    # Call the function
    o = read_config(Path(model_data_clipped_path, "settings_geom.toml"))

    # Assert output
    assert isinstance(o, dict)
    assert o.get("exposure") is not None


def test_read_csv(tmp_path: Path):
    with open(Path(tmp_path, "foo.csv"), "w") as _w:
        _w.write("depth,rs1\n")
        _w.write("0,0\n")
        _w.write("1,1\n")
    # Call the function
    o = read_csv(Path(tmp_path, "foo.csv"))

    # Assert output
    assert isinstance(o, pd.DataFrame)
    assert "rs1" in o.columns.tolist()


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


def test_read_grid_zarr(tmp_path: Path, hazard_clipped: xr.Dataset):
    p = Path(tmp_path, "foo.zarr")
    # Write the data in the format that is to be read
    write_grid(data=hazard_clipped, write_path=p, chunks={"x": 2, "y": 2})

    # Call the function
    o = read_grid(p)

    # Assert the output
    assert isinstance(o, xr.Dataset)
    assert "flood_event" in o.data_vars
    # Assert the data is in a north south orientation
    assert o.raster.res[1] < 0
    np.testing.assert_array_equal(
        o["flood_event"].values,
        hazard_clipped["flood_event"].values,
    )


def test_read_grid_tif(tmp_path: Path, hazard_clipped: xr.Dataset):
    p = Path(tmp_path, "foo.tif")
    # Write the data in the format that is to be read
    hazard_clipped["flood_event"].raster.to_raster(p)

    # Call the function
    o = read_grid(p)

    # Assert the output, the data is in a north south orientation
    assert o.raster.res[1] < 0
    np.testing.assert_array_equal(
        o.values,
        hazard_clipped["flood_event"].values,
    )


def test_read_grid_str(model_data_clipped_path: Path):
    # Call the function with a string path
    o = read_grid(str(Path(model_data_clipped_path, "hazard.nc")))

    # Assert the output
    assert "flood_event" in o.data_vars


def test_read_grid_errors(tmp_path: Path):
    # Call the function with an extension that is not supported
    with pytest.raises(
        ValueError,
        match="Cannot read file with extension: '.foo'",
    ):
        read_grid(Path(tmp_path, "foo.foo"))
