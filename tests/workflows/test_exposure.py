from pathlib import Path

import pandas as pd
from hydromt import DataCatalog

from hydromt_fiat.workflows import exposure_grid_data


def test_exposure_grid_data(build_data_catalog, build_region_gdf, tmp_path):
    dc = DataCatalog(build_data_catalog)
    raster_source = dc.get_source("flood_event")
    file_name = Path(raster_source.uri).name
    linking_table = pd.DataFrame(
        data=[{"exposure": file_name, "vulnerability": "damage_function_file"}]
    )
    linking_table_fp = tmp_path / "linking_table.csv"
    linking_table.to_csv(linking_table_fp)

    ds = exposure_grid_data(
        grid_like=None,
        region=build_region_gdf,
        data_catalog=dc,
        exposure_files=["flood_event"],
        linking_table=linking_table_fp,
    )
    assert ds
