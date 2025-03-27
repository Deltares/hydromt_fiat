"""Exposure workflows."""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import xarray as xr
from hydromt import DataCatalog

from hydromt_fiat.workflows.utils import _process_grid

__all__ = ["exposure_grid_data"]


def exposure_grid_data(
    grid_like: xr.Dataset,
    region: gpd.GeoDataFrame,
    data_catalog: DataCatalog,
    exposure_files: str | Path | list[str | Path],
    linking_table: str | Path,
    exposure_col: str = "exposure",
    vulnerability_col: str = "vulnerability",
) -> xr.Dataset:
    """Read and transform exposure grid data.

    Parameters
    ----------
    exposure_files : str | Path | list[str  |  Path]
        _description_
    linking_table : str | Path
        _description_

    Returns
    -------
    xr.Dataset
        Transformed and unified exposure grid
    """
    linking_table = pd.read_csv(linking_table)

    for exposure_file in exposure_files:
        exposure_file = Path(exposure_file)

        if exposure_file.name not in linking_table[exposure_col]:
            raise ValueError(
                f"{exposure_file.name} exposure grid file name missing in linking table"
            )
        da = data_catalog.get_rasterdataset(exposure_file, geom=region)
        da_name = exposure_file.stem.lower()
        da = _process_grid(da=da, da_name=da_name)
        damage_fn = linking_table.loc[
            linking_table[exposure_col] == exposure_file.stem, vulnerability_col
        ]
        damage_fn
