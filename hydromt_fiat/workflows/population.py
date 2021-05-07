import logging
import numpy as np
import pandas as pd
import sys
import xarray as xr
from hydromt import gis_utils, io, raster


logger = logging.getLogger(__name__)


def downscale_population(exposure_da):
    # create an index grid that connects the clipped population and buildings maps
    pop_bld_idx = exposure_da["pop"].raster.nearest_index(
        dst_crs=exposure_da["bld"].raster.crs,
        dst_transform=exposure_da["bld"].raster.transform,
        dst_width=exposure_da["bld"].raster.width,
        dst_height=exposure_da["bld"].raster.height,
    )

    # create a population and buildings density grid
    pop_density = create_density_grid(exposure_da["pop"])
    bld_density = create_density_grid(exposure_da["bld"])

    for idx in np.unique(pop_bld_idx.values):  # TODO: Use groupby
        # calculate the total building area and count
        x_res, y_res = exposure_da["bld"].raster.res
        bld_mask = pop_bld_idx.where(pop_bld_idx == idx, drop=True).indexes
        bld_area = np.count_nonzero(
            ~np.isnan(
                exposure_da["bld"].sel(indexers=bld_mask, method="nearest").values
            )
        ) * abs(x_res * y_res)
        total_bld = (
            exposure_da["bld"].sel(indexers=bld_mask, method="nearest").values.sum()
        )

        # calculate the total population count
        x_res, y_res = exposure_da["pop"].raster.res
        x_idx, y_idx = exposure_da["pop"].raster.idx_to_xy(idx)
        selection = {"x": x_idx, "y": y_idx}
        pop_density = exposure_da["pop"].sel(
            indexers=selection, method="nearest"
        ).values[0, 0].astype("float64") / abs(x_res * y_res)
        total_pop = bld_area * pop_density

        # calculate the population per building value and check if the number is valid and correct if necessary
        try:
            pop_per_bld = total_pop / total_bld

            # Raise if both the total population and buildings counts are zero
            assert np.isnan(pop_per_bld) == False

            # Raise if the total buildings count is zero
            assert np.isinf(pop_per_bld) == False

        except AssertionError:
            logger.debug("Handled the AssertionError.")
            pop_per_bld = 0

        # assign the calculated population per building to the built-up grid cells
        exposure_da["bld"].sel(indexers=bld_mask, method="nearest") * pop_per_bld

    test = 0

    # Create an index grid that connects the clipped population map with the connection grid

    return da


def create_density_grid(ds):
    """Returns a DataArray or DataSet containing the density in unit/m2 of the reference grid(s) ds.

    Parameters
    ----------
    ds : xarray.DataArray or xarray.DataSet
        DataArray or xarray.DataSet containing reference grid(s).

    Returns
    -------
    ds_out : xarray.DataArray or xarray.DataSet
        DataArray or xarray.DataSet containing the density in unit/m2 of the reference grid(s).
    """

    # create a grid that contains the area in m2 per grid cell.
    if ds.raster.crs.is_geographic:
        area = get_area_grid(ds)

    elif ds.raster.crs.is_projected:
        area = ds.raster.res[0] ** 2

    # create a grid that contains the density in unit/m2 per grid cell
    ds_out = ds / area

    return ds_out


def get_area_grid(ds):
    """Returns a DataArray containing the area in m2 of the reference grid ds.

    Parameters
    ----------
    ds : xarray.DataArray or xarray.DataSet
        DataArray or xarray.DataSet containing reference grid(s).

    Returns
    -------
    da_out : xarray.DataArray
        DataArray containing the area in m2 of the reference grid.
    """

    area = gis_utils.reggrid_area(
        ds.raster.ycoords.values,
        ds.raster.xcoords.values,
    )

    da_out = xr.DataArray(
        data=area.astype("float32"),
        coords=ds.raster.coords,
        dims=ds.raster.dims,
    )

    return da_out
