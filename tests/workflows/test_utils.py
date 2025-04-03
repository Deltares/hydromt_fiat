import logging

import xarray as xr
from hydromt import DataCatalog

from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray


def test_process_dataarray(build_data_catalog):
    dc = DataCatalog(build_data_catalog)
    da = dc.get_rasterdataset("flood_event")
    da = _process_dataarray(da=da, da_name="flood_dataarray")
    assert da.encoding["_FillValue"] is None
    assert da.name == "flood_dataarray"
    assert "grid_mapping" not in da.encoding.keys()


def test_merge_dataarrays(caplog, build_data_catalog, build_region_small_gdf):
    dc = DataCatalog(build_data_catalog)
    da1 = dc.get_rasterdataset("flood_event", geom=build_region_small_gdf)
    da2 = dc.get_rasterdataset("flood_event", geom=build_region_small_gdf)
    das = [da1, da2]
    caplog.set_level(logging.WARNING)
    ds = _merge_dataarrays(grid_like=None, dataarrays=das)
    warning_msg = (
        "grid_like argument not given, defaulting to first grid file in"
        " the list of grids"
    )
    assert warning_msg in caplog.text
    assert isinstance(ds, xr.Dataset)
