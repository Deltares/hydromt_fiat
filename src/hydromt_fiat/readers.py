"""Standalone reader functions for HydroMT-FIAT."""

import logging
from pathlib import Path
from typing import Any, cast

import geopandas as gpd
import pandas as pd
import xarray as xr
from hydromt.readers import open_nc, read_toml

from hydromt_fiat.gis.raster_utils import force_ns
from hydromt_fiat.utils import OBJECT__ID

__all__ = [
    "read_config",
    "read_csv",
    "read_geoms",
    "read_grid",
]

logger = logging.getLogger(f"hydromt.{__name__}")


def read_config(
    read_path: Path | str,
) -> dict[str, Any]:
    """Read a FIAT settings file."""
    logger.info(f"Reading config file at {Path(read_path).as_posix()}")
    data = read_toml(read_path)
    return data


def read_csv(
    read_path: Path | str,
    **kwargs,
) -> pd.DataFrame:
    """Read a FIAT related csv file.

    Nothing more than calling pandas.

    Parameters
    ----------
    read_path : Path | str
        The path to the file.
    **kwargs : dict
        Additional keyword arguments that are passed to the
        `pandas.read_csv` function.

    Returns
    -------
    pd.DataFrame
        The tabular data.
    """
    logger.info(f"Reading csv file at {Path(read_path).as_posix()}")
    data = pd.read_csv(read_path, **kwargs)
    return data


def read_geoms(
    read_path: Path | str,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Read a FIAT related geometry file.

    Backwards compatible with older models where exposure data was separated into
    a vector file and a csv file.

    Parameters
    ----------
    read_path : Path | str
        The path to the file. If a csv file with the same name is present next to the
        vector file, this file is read too and will merged with the vector
        file based on the 'object_id' column.
    **kwargs : dict
        Additional keyword arguments that are passed to the
        `geopandas.read_file` function.

    Returns
    -------
    gpd.GeoDataFrame
        The geometry data.
    """
    logger.info(f"Reading geometry file at {Path(read_path).as_posix()}")
    data = cast(gpd.GeoDataFrame, gpd.read_file(read_path, **kwargs))
    # Check for data in csv file, this has to be merged
    # TODO this should be solved better with help of the config file
    csv_path = Path(read_path).with_suffix(".csv")
    if csv_path.is_file():
        csv_data = pd.read_csv(csv_path)
        data = data.merge(csv_data, on=OBJECT__ID)
    return data


def read_grid(
    read_path: Path | str,
    **kwargs,
) -> xr.Dataset:
    """Read a FIAT related raster file.

    Parameters
    ----------
    read_path : Path | str
        The path to the file.
    **kwargs : dict
        Additional keyword arguments to be passed to the `open_dataset` function
        from xarray.

    Returns
    -------
    xr.Dataset
        The gridded data in a north south orientation.
    """
    logger.info(f"Reading grid file at {Path(read_path).as_posix()}")
    ds = open_nc(
        read_path,
        **kwargs,
    )
    ds = force_ns(ds)
    return ds
