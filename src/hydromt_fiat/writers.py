"""Standalone writer functions for HydroMT-FIAT."""

import copy
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import tomlkit
import xarray as xr
from hydromt.writers import write_nc as _write_nc
from zarr import consolidate_metadata
from zarr.abc.codec import BaseCodec
from zarr.codecs import BloscCodec

from hydromt_fiat.gis.raster_utils import cell_size, force_ns
from hydromt_fiat.utils import AREA__SQM

__all__ = [
    "write_config",
    "write_csv",
    "write_geoms",
    "write_grid",
    "write_nc",
]

TIFF_KWARGS = dict(
    driver="GTiff",
    tiled=True,
    blockxsize=256,
    blockysize=256,
    profile="COG",
)
TIFF_COMPRESSION = dict(
    compress="deflate",
    predictor=2,
)
ZARR_COMPRESSION = BloscCodec(cname="zlib", clevel=2, shuffle="shuffle")

logger = logging.getLogger(f"hydromt.{__name__}")


def _write_dir(
    write_path: Path | str,
) -> None:
    """Ensure the writing directory."""
    write_path = Path(write_path)
    write_dir = write_path.parent
    write_dir.mkdir(parents=True, exist_ok=True)


def _write_zarr(
    ds: xr.Dataset | xr.DataArray,
    write_path: Path | str,
    chunks: dict[str, int],
    compressor: BaseCodec[Any, Any] | None = None,
) -> None:
    """Export dataset to a zarr archive.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset to be exported to zarr archive.
    write_path : Path | str
        The file path for the outgoing zarr archive.
    chunks : dict
        A dictionary describing the chunk size per dimension.
    compressor : BaseCodec, optional
        The compressor used to compress the zarr archive. By default None.
    """
    if isinstance(ds, xr.DataArray):
        ds = ds.to_dataset()

    # Set the codec
    encoding = {}
    ds.encoding = {}
    for v in ds.data_vars:
        ds[v].encoding = {}
        if compressor is not None:
            encoding[v] = {"compressors": [compressor]}

    # Write and consolidate
    ds.chunk(chunks).to_zarr(
        write_path,
        compute=True,
        safe_chunks=True,
        consolidated=False,
        encoding=encoding,
    )
    consolidate_metadata(write_path)


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


def write_nc(
    data: xr.Dataset,
    write_path: Path | str,
    overwrite: bool = True,
    **kwargs,
) -> None:
    """Write FIAT related dataset to a netCDF file.

    Parameters
    ----------
    data : xr.Dataset
        The data to write.
    write_path : Path | str
        The path to write to.
    overwrite : bool, optional
        Whether or not to overwrite a possibly existing file, by default True.
    **kwargs : dict
        Additional keyword arguments to be passed to the `to_netcdf` method from
        xarray.
    """
    _write_dir(write_path)
    logger.info(f"Writing netcdf file to {Path(write_path).as_posix()}")
    _write_nc(
        ds=data,
        file_path=write_path,
        compress=True,
        force_overwrite=overwrite,
        to_netcdf_kwargs=kwargs,
    )


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
        Additional keyword arguments to be passed to the write functions corresponding
        to the extension/ driver.
    """
    _write_dir(write_path)
    write_path = Path(write_path)
    logger.info(f"Writing grid file to {write_path.as_posix()}")
    # Set the cell area size
    data.attrs.update({AREA__SQM: cell_size(data)})
    # Write according to the extension
    ext = write_path.suffix
    match ext:
        case ".nc":
            _write_nc(
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
        case ".zarr":
            compressor = None
            if compress:
                compressor = ZARR_COMPRESSION
            _write_zarr(
                ds=data,
                write_path=write_path,
                compressor=compressor,
                **kwargs,
            )
        case ".tif":
            write_kwargs = copy.deepcopy(TIFF_KWARGS)
            if compress:
                write_kwargs.update(TIFF_COMPRESSION)
            force_ns(data).raster.to_raster(
                write_path,
                **write_kwargs,
            )
        case _:
            raise ValueError(f"Cannot write file with '{ext}' extension")
