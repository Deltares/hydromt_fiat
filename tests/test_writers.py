import tomllib
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
import xarray as xr

from hydromt_fiat.utils import AREA__SQM
from hydromt_fiat.writers import (
    write_config,
    write_csv,
    write_geoms,
    write_grid,
    write_nc,
)


def test_write_config(tmp_path: Path, config_dummy: dict[str, Any]):
    config_dummy["hazard"]["file"] = "foo.nc"
    config_dummy["vulnerability"]["file"] = "foo.csv"
    p = Path(tmp_path, "settings.toml")
    # Call the functions
    write_config(data=config_dummy, write_path=p)

    # Assert the file is there
    assert p.is_file()
    # Read back in and assert
    with open(p, "r") as reader:
        data = tomllib.loads(reader.read())
    assert "hazard" in data
    assert data == config_dummy


def test_write_csv(tmp_path: Path):
    p = Path(tmp_path, "foo.csv")
    # Call the functions
    write_csv(data=pd.DataFrame(data=[1, 2, 3, 4]), write_path=p)

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


def test_write_grid_attrs(tmp_path: Path, hazard_clipped: xr.Dataset):
    p = Path(tmp_path, "foo.nc")
    # Call the functions
    write_grid(data=hazard_clipped, write_path=p)

    # Assert the cell area is set
    assert hazard_clipped.attrs[AREA__SQM] == 10000
    with xr.open_dataset(p) as ds:
        assert ds.attrs[AREA__SQM] == 10000


def test_write_grid_dir(tmp_path: Path, hazard_clipped: xr.Dataset):
    p = Path(tmp_path, "foo", "bar.nc")
    # Call the functions
    write_grid(data=hazard_clipped, write_path=p)

    # Assert the file, with its directory
    assert p.is_file()


@pytest.mark.parametrize("compress", [True, False])
def test_write_grid_zarr(
    tmp_path: Path,
    compress: bool,
    hazard_clipped: xr.Dataset,
):
    p = Path(tmp_path, "foo.zarr")
    # Call the functions
    write_grid(
        data=hazard_clipped,
        write_path=p,
        compress=compress,
        chunks={"x": 2, "y": 2},
    )

    # Assert the archive
    assert p.is_dir()
    assert Path(p, "zarr.json").is_file()
    # Assert it is readable by xarray and holds the same data
    with xr.open_zarr(p, mask_and_scale=False) as ds:
        assert "flood_event" in ds.data_vars
        np.testing.assert_array_equal(
            ds["flood_event"].values,
            hazard_clipped["flood_event"].values,
        )


@pytest.mark.xfail(
    strict=True,
    reason="write_grid calls 'to_raster' on the RasterDataset accessor",
)
@pytest.mark.parametrize("compress", [True, False])
def test_write_grid_tif(
    tmp_path: Path,
    compress: bool,
    hazard_clipped: xr.Dataset,
):
    p = Path(tmp_path, "foo.tif")
    # Call the functions
    write_grid(data=hazard_clipped, write_path=p, compress=compress)

    # Assert the file
    assert p.is_file()
    # Assert it is readable by rasterio
    with rasterio.open(p) as src:
        assert src.count == len(hazard_clipped.data_vars)
        assert src.crs.to_epsg() == 28992


def test_write_grid_errors(tmp_path: Path, hazard_clipped: xr.Dataset):
    # Call the function with an extension that is not supported
    with pytest.raises(
        ValueError,
        match="Cannot write file with '.foo' extension",
    ):
        write_grid(data=hazard_clipped, write_path=Path(tmp_path, "foo.foo"))


def test_write_nc(tmp_path: Path, hazard_clipped: xr.Dataset):
    p = Path(tmp_path, "foo.nc")
    # Call the functions
    write_nc(data=hazard_clipped, write_path=p)

    # Assert the file
    assert p.is_file()
    # Assert it is readable by xarray
    with xr.open_dataset(p) as ds:
        assert "flood_event" in ds.data_vars


def test_write_nc_dir(tmp_path: Path, hazard_clipped: xr.Dataset):
    p = Path(tmp_path, "foo", "bar.nc")
    # Call the functions
    write_nc(data=hazard_clipped, write_path=p)

    # Assert the file, with its directory
    assert p.is_file()
