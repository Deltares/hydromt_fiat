"""Hazard workflows."""

import logging
from pathlib import Path

import geopandas as gpd
import xarray as xr
from hydromt import DataCatalog
from hydromt.model.processes.grid import grid_from_rasterdataset

__all__ = ["hazard_data"]


logger = logging.getLogger(f"hydromt.{__name__}")


def hazard_data(
    grid_like: xr.Dataset | None,
    region: gpd.GeoDataFrame,
    data_catalog: DataCatalog,
    hazard_fnames: list[str],
    hazard_type: str | None,
    return_periods: list[int] | None = None,
    *,
    risk: bool,
) -> xr.Dataset:
    """Parse hazard data files to xarray dataset.

    Parameters
    ----------
    grid_like: xr.Dataset | None
        Grid dataset that serves as an example dataset for transforming the input data
    region: gpd.GeoDataFrame
        Region geometry used for reading data from data catalog
    data_catalog : DataCatalog
        Model data catalog
    hazard_fnames : list[str]
        Names or paths of hazard files
    hazard_type : str | None
        Type of hazard
    risk : bool
        Designate hazard files for risk analysis
    return_periods : list[int] | None, optional
        List of return periods, by default None

    Returns
    -------
    xr.Dataset
        Unified xarray dataset containing the hazard data
    """
    hazard_dataarrays = []
    for i, hazard_file in enumerate(hazard_fnames):
        da = data_catalog.get_rasterdataset(hazard_file, geom=region)

        # Convert to gdal compliant
        da.encoding["_FillValue"] = None
        da: xr.DataArray = da.raster.gdal_compliant()

        # ensure variable name is lowercase
        da_name = Path(hazard_file).stem.lower()
        da = da.rename(da_name)

        # Check if map is rotated and if yes, reproject to a non-rotated grid
        if "xc" in da.coords:
            logger.warning(
                "Hazard map is rotated. It will be reprojected"
                " to a none rotated grid using nearest neighbor"
                "interpolation"
            )
            da: xr.DataArray = da.raster.reproject(dst_crs=da.rio.crs)
        if "grid_mapping" in da.encoding:
            _ = da.encoding.pop("grid_mapping")

        rp = f"(rp {return_periods[i]})" if risk else ""
        logger.info(f"Added {hazard_type} hazard map: {da_name} {rp}")

        if not risk:
            # Set the event data arrays to the hazard grid component
            da = da.assign_attrs(
                {
                    "name": da_name,
                    "type": hazard_type,
                    "analysis": "event",
                }
            )

        hazard_dataarrays.append(da)
    if not grid_like:
        grid_like = hazard_dataarrays[0].to_dataset()

    ds = xr.merge(hazard_dataarrays)

    # Reproject to gridlike
    ds = grid_from_rasterdataset(grid_like=grid_like, ds=ds)
    da_names = [d.name for d in hazard_dataarrays]

    if risk:
        ds = ds.assign_attrs(
            {
                "return_period": return_periods,
                "type": hazard_type,
                "name": da_names,
                "analysis": "risk",
            }
        )

    else:
        ds = ds.assign_attrs(
            {"analysis": "event", "type": hazard_type, "name": da_names}
        )
    return ds
