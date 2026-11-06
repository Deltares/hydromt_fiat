"""Generic grid-based workflows."""

import numpy as np
import xarray as xr
from hydromt.gis import full_like

__all__ = ["grid_fixed_from_finite"]


def grid_fixed_from_finite(
    data: xr.DataArray,
    value: float | int,
) -> xr.DataArray:
    """Create a fixed value grid based on the location of finite values in another.

    Parameters
    ----------
    data : xr.DataArray
        The blueprint grid data with finite values.
    value : float | int
        The fixed value to set.

    Returns
    -------
    xr.DataArray
        The resulting data array.
    """
    # Mask with the nodata value
    mask = data == data.raster.nodata

    # Nodata value
    nodata = -9999
    # Create a new data array based on the current one
    da = full_like(data, nodata=nodata, fill_value=nodata, dtype=np.float32, lazy=True)
    da.attrs = {"_FillValue": nodata}
    # Set the fixed value based on the mask
    da = da.where(mask, value)

    # Return the data
    return da
