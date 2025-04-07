"""Exposure workflows."""

import logging

import geopandas as gpd
import pandas as pd
import xarray as xr

from hydromt_fiat.workflows.utils import _merge_dataarrays, _process_dataarray

__all__ = ["exposure_geom_linking", "exposure_grid_data"]

logger = logging.getLogger(f"hydromt.{__name__}")


def exposure_geom_linking(
    exposure_data: gpd.GeoDataFrame,
    exposure_type_column: str,
    vulnerability: pd.DataFrame,
    *,
    exposure_linking: pd.DataFrame | None,
) -> gpd.GeoDataFrame:
    """_summary_.

    Parameters
    ----------
    exposure_data : gpd.GeoDataFrame
        _description_
    exposure_type_column : str
        _description_
    vulnerability : pd.DataFrame
        _description_
    exposure_link_data : pd.DataFrame | None
        _description_

    Returns
    -------
    gpd.GeoDataFrame
        _description_
    """
    # Some checks
    if exposure_type_column not in exposure_data:
        raise KeyError(f"{exposure_type_column} not found in the exposure data")
    if exposure_linking is None:
        logger.warning(
            "No exposure link table provided, \
defaulting to exposure data object type"
        )
        exposure_linking = pd.DataFrame(
            {
                exposure_type_column: exposure_data[exposure_type_column].values,
                "object_type": exposure_data[exposure_type_column].values,
            }
        )
    if exposure_type_column not in exposure_linking:
        raise KeyError(f"{exposure_type_column} not found in the provided linking data")

    # Make sure that there are no duplicated in the linking
    exposure_linking = exposure_linking.drop_duplicates(
        exposure_type_column,
        keep="first",
    )
    # Also drop the remaining unused columns
    exposure_linking = exposure_linking[[exposure_type_column, "object_type"]]

    # Link the data into a new column
    exposure_data = pd.merge(
        exposure_data,
        exposure_linking,
        on=exposure_type_column,
        how="inner",
        validate="many_to_many",
    )

    # Get the unique exposure types
    headers = vulnerability["exposure_type"]
    if "subtype" in vulnerability:
        headers = vulnerability["exposure_type"] + "_" + vulnerability["subtype"]

    # Go through the unique new headers
    for header in headers.unique().tolist():
        link = vulnerability[headers == header][["link", "curve_id"]]
        link.rename(
            {"link": "object_type", "curve_id": f"fn_{header}"},
            axis=1,
            inplace=True,
        )
        # And merge the data
        exposure_data = exposure_data.merge(link, on="object_type")

    return exposure_data


def exposure_grid_data(
    grid_like: xr.Dataset | None,
    exposure_data: dict[str, xr.DataArray],
    exposure_linking: pd.DataFrame,
) -> xr.Dataset:
    """Read and transform exposure grid data.

    Parameters
    ----------
    grid_like : xr.Dataset | None
        Xarray dataset that is used to transform exposure data with. If set to None,
        the first data array in exposure_files is used to transform the data.
    exposure_files : dict[str, xr.DataArray]
        Dictionary containing name of exposure file and associated data
    linking_table : pd.DataFrame
        Table containing the names of the exposure files and corresponding
        vulnerability curves.

    Returns
    -------
    xr.Dataset
        Transformed and unified exposure grid
    """
    exposure_dataarrays = []
    exposure_col = "type"
    vulnerability_col = "curve_id"

    for da_name, da in exposure_data.items():
        if da_name not in exposure_linking[exposure_col].values:
            fn_damage = da_name
            logger.warning(
                f"Exposure file name, '{da_name}', not found in linking table."
                f" Setting damage curve name attribute to '{da_name}'."
            )
        else:
            fn_damage = exposure_linking.loc[
                exposure_linking[exposure_col] == da_name, vulnerability_col
            ].values[0]
        da = _process_dataarray(da=da, da_name=da_name)
        da = da.assign_attrs({"fn_damage": fn_damage})
        exposure_dataarrays.append(da)

    return _merge_dataarrays(grid_like=grid_like, dataarrays=exposure_dataarrays)
