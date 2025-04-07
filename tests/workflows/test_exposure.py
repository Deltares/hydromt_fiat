import logging

import pandas as pd
import xarray as xr
from hydromt import DataCatalog

from hydromt_fiat.workflows import exposure_grid_data


def test_exposure_grid_data(build_data_catalog, build_region_gdf, caplog):
    dc = DataCatalog(build_data_catalog)
    linking_table = pd.DataFrame(
        data=[{"type": "flood_event", "curve_id": "damage_function_file"}]
    )
    exposure_files = {
        "flood_event": dc.get_rasterdataset("flood_event", geom=build_region_gdf)
    }
    ds = exposure_grid_data(
        grid_like=None,
        exposure_files=exposure_files,
        linking_table=linking_table,
    )
    assert isinstance(ds, xr.Dataset)
    assert ds.attrs.get("fn_damage") == "damage_function_file"


def test_exposure_grid_data_no_linking_table_match(
    build_data_catalog, build_region_gdf, caplog
):
    # Test without matching exposure file name in linking table
    dc = DataCatalog(build_data_catalog)
    exposure_files = {
        "flood_event": dc.get_rasterdataset("flood_event", geom=build_region_gdf)
    }
    caplog.set_level(logging.WARNING)
    linking_table = pd.DataFrame(
        data=[{"type": "event", "curve_id": "damage_function_file"}]
    )

    ds = exposure_grid_data(
        grid_like=None, exposure_files=exposure_files, linking_table=linking_table
    )
    log_msg = (
        "Exposure file name, 'flood_event', not found in linking table."
        " Setting damage curve name attribute to 'flood_event'."
    )
    assert log_msg in caplog.text

    # Check if damage function defaults to exposure file name
    assert ds.attrs.get("fn_damage") == "flood_event"
