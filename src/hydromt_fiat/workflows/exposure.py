"""Exposure workflows."""

import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd
import xarray as xr
from hydromt import DataCatalog

from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray

__all__ = ["exposure_grid_data"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_grid_data(
    grid_like: xr.Dataset | None,
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
    exposure_dataarrays = []
    exposure_files = (
        [exposure_files] if isinstance(exposure_files, str) else exposure_files
    )

    for exposure_file in exposure_files:
        exposure_fn = Path(exposure_file).stem
        if exposure_fn not in linking_table[exposure_col].values:
            fn_damage = exposure_fn
            logger.warning(
                f"Exposure file name, '{exposure_fn}', not found in linking table."
                f" Setting damage curve file name attribute to '{exposure_fn}'."
            )
        else:
            fn_damage = linking_table.loc[
                linking_table[exposure_col] == exposure_fn, vulnerability_col
            ].values[0]
        da = data_catalog.get_rasterdataset(exposure_file, geom=region)
        da = _process_dataarray(da=da, da_name=exposure_fn)
        da = da.assign_attrs({"fn_damage": fn_damage})
        exposure_dataarrays.append(da)

    return _merge_dataarrays(grid_like=grid_like, dataarrays=exposure_dataarrays)
