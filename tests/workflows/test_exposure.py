import logging

import pandas as pd
import xarray as xr
from hydromt import DataCatalog

from hydromt_fiat.workflows import exposure_grid_data


def test_exposure_grid_data(build_data_catalog, build_region_gdf, tmp_path, caplog):
    dc = DataCatalog(build_data_catalog)
    linking_table = pd.DataFrame(
        data=[{"exposure": "flood_event", "vulnerability": "damage_function_file"}]
    )
    linking_table_fp = tmp_path / "linking_table.csv"
    linking_table.to_csv(linking_table_fp, index=False)

    ds = exposure_grid_data(
        grid_like=None,
        region=build_region_gdf,
        data_catalog=dc,
        exposure_files=["flood_event"],
        linking_table=linking_table_fp,
    )
    assert isinstance(ds, xr.Dataset)
    assert ds.attrs.get("damage_function") == "damage_function_file"

    # Test without matching exposure file name in linking table
    caplog.set_level(logging.WARNING)
    linking_table = pd.DataFrame(
        data=[{"exposure": "event", "vulnerability": "damage_function_file"}]
    )
    linking_table.to_csv(linking_table_fp, index=False)

    ds = exposure_grid_data(
        grid_like=None,
        region=build_region_gdf,
        data_catalog=dc,
        exposure_files=["flood_event"],
        linking_table=linking_table_fp,
    )
    log_msg = (
        "Exposure file name, 'flood_event', not found in linking table."
        " Setting damage curve file name attribute to 'flood_event'."
    )
    assert log_msg in caplog.text

    # Check if damage function defaults to exposure file name
    assert ds.attrs.get("fn_damage") == "flood_event"
