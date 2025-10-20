import logging

import geopandas as gpd
import pytest
import xarray as xr
from hydromt import DataCatalog

from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray


def test_process_dataarray(build_data_catalog: DataCatalog):
    da = build_data_catalog.get_rasterdataset("flood_event")
    da = _process_dataarray(da=da, da_name="flood_dataarray")
    assert da.encoding["_FillValue"] is None
    assert da.name == "flood_dataarray"
    assert "grid_mapping" not in da.encoding.keys()


def test_merge_dataarrays(
    caplog: pytest.LogCaptureFixture,
    build_region_small: gpd.GeoDataFrame,
    build_data_catalog: DataCatalog,
):
    da1 = build_data_catalog.get_rasterdataset("flood_event", geom=build_region_small)
    da2 = build_data_catalog.get_rasterdataset("flood_event", geom=build_region_small)
    das = [da1, da2]
    caplog.set_level(logging.WARNING)
    ds = _merge_dataarrays(grid_like=None, dataarrays=das)
    warning_msg = "No known grid provided to reproject to, \
defaulting to first specified grid for transform and extent"
    assert warning_msg in caplog.text
    assert isinstance(ds, xr.Dataset)
