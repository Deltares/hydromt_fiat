"""Standalone writer functions for HydroMT-FIAT."""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import tomlkit
import xarray as xr
from hydromt.writers import write_nc

from hydromt_fiat.gis.raster_utils import force_ns

__all__ = [
    "write_config",
    "write_csv",
    "write_geoms",
    "write_grid",
]

logger = logging.getLogger(f"hydromt.{__name__}")


def _write_dir(
    write_path: Path | str,
) -> None:
    """Ensure the writing directory."""
    write_path = Path(write_path)
    write_dir = write_path.parent
    write_dir.mkdir(parents=True, exist_ok=True)


def write_config(
    data: dict[str, Any],
    write_path: Path | str,
) -> None:
    """Writer the FIAT settings toml."""
    _write_dir(write_path)
    logger.info(f"Writing config file to {Path(write_path).as_posix()}")
    with open(write_path, "w") as writer:
        tomlkit.dump(data, writer)


def write_csv(
    data: pd.DataFrame,
    write_path: Path | str,
    **kwargs,
) -> None:
    """Write FIAT related tabular data to a csv file.

    Nothing more than calling pandas.

    Parameters
    ----------
    data : pd.DataFrame
        The data to write.
    write_path : Path | str
        The path to write to.
    **kwargs : dict
        Additional keyword arguments that are passed to the
        `pandas.to_csv` function.
    """
    _write_dir(write_path)
    logger.info(f"Writing csv file to {Path(write_path).as_posix()}")
    data.to_csv(write_path, **kwargs)


def write_geoms(
    data: gpd.GeoDataFrame,
    write_path: Path | str,
    **kwargs,
) -> None:
    """Write FIAT related geometries to a vector file.

    Nothing more than calling geopandas.

    Parameters
    ----------
    data : gpd.GeoDataFrame
        The data to write.
    write_path : Path | str
        The path to write to.
    **kwargs : dict
        Additional keyword arguments that are passed to the
        `geopandas.to_file` function.
    """
    _write_dir(write_path)
    logger.info(f"Writing geometry file to {Path(write_path).as_posix()}")
    data.to_file(write_path, **kwargs)


def write_grid(
    data: xr.Dataset,
    write_path: Path | str,
    compress: bool = False,
    gdal_compliant: bool = True,
    overwrite: bool = True,
    **kwargs,
) -> None:
    """Write FIAT related grid data.

    Always written in a north-south orientation.

    Parameters
    ----------
    data : xr.Dataset
        The data to write.
    write_path : Path | str
        The path to write to.
    compress : bool, optional
        Whether or not to compress the data, by default False.
    gdal_compliant : bool, optional
        Whether or not to write the data in a gdal compliant manner, i.e. in such a
        way that the data can be understood by GDAL. By default True.
    overwrite : bool, optional
        Whether or not to overwrite a possibly existing file, by default True.
    **kwargs : dict
        Additional keyword arguments to be passed to the `to_netcdf` method from
        xarray.
    """
    _write_dir(write_path)
    logger.info(f"Writing grid file to {Path(write_path).as_posix()}")
    write_nc(
        force_ns(data),
        file_path=write_path,
        compress=compress,
        gdal_compliant=gdal_compliant,
        rename_dims=False,
        force_overwrite=overwrite,
        force_sn=False,
        progressbar=True,
        to_netcdf_kwargs=kwargs,
    )
