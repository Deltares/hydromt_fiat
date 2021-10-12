from hydromt import gis_utils, raster
import logging
import numpy as np
import xarray as xr

logger = logging.getLogger(__name__)


def create_population_per_building_map(
    da_bld,
    da_pop,
    ds_like=None,
    logger=logger,
):
    """Create a population per built-up grid cell layer.

    Parameters
    ----------
    da_bld: xarray.DataArray
        xarray.DataArray containing a numerical indication whether a grid cell is part of the built-up area or not.
    pop_fn: xarray.DataArray
        xarray.DataArray containing the number of inhabitants per grid cell.
    ds_like: xarray.DataArray or xarray.DataSet
        xarray.DataArray or xarray.DataSet containing the reference grid(s) projection.

    Returns
    -------
    ds_count : xarray.DataSet
        xarray.DataSet containing .
    """

    logger.debug("Creating the population per building map.")

    # Correct the buildings and population maps.
    da_bld = da_bld.where(da_bld <= 0, other=1)
    da_pop = da_pop.where(da_pop != da_pop.raster.nodata, other=0)
    da_bld.raster.set_nodata(nodata=0)
    da_pop.raster.set_nodata(nodata=0)

    # Get the area and density grids.
    da_like_area = get_area_grid(ds_like)
    da_bld_density = get_density_grid(da_bld).rename("bld_density")
    da_pop_density = get_density_grid(da_pop).rename("pop_density")

    # Get the (average) grid resolutions in meters.
    da_bld_res = get_grid_resolution(da_bld)
    da_pop_res = get_grid_resolution(da_pop)
    ds_like_res = get_grid_resolution(ds_like)

    # Creating the population per building map.
    if da_bld_res > ds_like_res or da_pop_res > ds_like_res:
        if da_pop_res > da_bld_res:
            da_low_res = da_pop
            da_high_res = da_bld
        else:
            da_low_res = da_bld
            da_high_res = da_pop

        # Get the area grid.
        da_bld_area = get_area_grid(da_bld).rename("bld_area")

        # Create an index grid that connects the population and buildings maps.
        da_idx = da_low_res.raster.nearest_index(
            dst_crs=da_high_res.raster.crs,
            dst_transform=da_high_res.raster.transform,
            dst_width=da_high_res.raster.width,
            dst_height=da_high_res.raster.height,
        ).rename("index")
        x_dim, y_dim = da_high_res.raster.x_dim, da_high_res.raster.y_dim
        da_idx[x_dim] = da_high_res.raster.xcoords
        da_idx[y_dim] = da_high_res.raster.ycoords

        # Create a population per buildings density map.
        df_sum = (
            xr.merge([da_bld, da_bld_area, da_idx])
            .stack(yx=(y_dim, x_dim))  # flatten to make dataframe
            .reset_coords(drop=True)
            .to_dataframe()
            .groupby("index")
            .sum()
        )  # TODO: Replace with xarray groupby sum after issue is solved (see https://github.com/pydata/xarray/issues/4473)!

        if da_pop_res > da_bld_res:
            ar_bld_count = np.full_like(da_pop, fill_value=0)
            ar_area_count = np.full_like(da_pop, fill_value=0)
            ar_bld_count.flat[[df_sum.index]] = df_sum["bld"]
            ar_area_count.flat[[df_sum.index]] = df_sum["bld_area"]
            ar_pop_bld_density = np.where(
                ar_bld_count != 0, (da_pop_density * ar_area_count) / ar_bld_count, 0
            )
        else:
            ar_pop_count = np.full_like(da_bld, fill_value=0)
            ar_area_count = np.full_like(da_bld, fill_value=0)
            ar_pop_count.flat[[df_sum.index]] = df_sum["pop"]
            ar_area_count.flat[[df_sum.index]] = df_sum["pop_area"]
            ar_pop_bld_density = np.where(
                da_bld_density != 0, ar_pop_count / (da_bld_density * ar_area_count), 0
            )
        da_pop_bld_density = raster.RasterDataArray.from_numpy(
            data=ar_pop_bld_density,
            transform=da_low_res.raster.transform,
            crs=da_low_res.raster.crs,
        )

        # Reproject the buildings, population and population per building density maps to the hazard projection.
        logger.debug(
            "Upscaling the building, population and population per building map to the hazard resolution."
        )
        da_bld_count = da_bld.raster.reproject_like(ds_like, method="sum")
        da_pop_count = da_pop_density.raster.reproject_like(
            ds_like, method="average"
        ) * da_like_area
        da_pop_bld_density = da_pop_bld_density.raster.reproject_like(
            ds_like, method="average"
        )

        # Create the population per building count maps.
        da_pop_bld_count = da_bld_count.where(
            da_bld_count == 0, other=da_pop_bld_density * da_bld_count
        )

    elif da_bld_res < ds_like_res and da_pop_res < ds_like_res:
        # Reproject the buildings and population maps to the hazard projection.
        logger.debug(
            "Downscaling the building and population maps to the hazard resolution."
        )
        da_bld_count = da_bld.raster.reproject_like(ds_like, method="sum")
        da_pop_count = da_pop.raster.reproject_like(ds_like, method="sum")

        # Create the population per building count maps.
        da_pop_bld_count = da_bld_count.where(
            da_bld_count == 0, other=da_pop_count
        )

    # Merge the output DataArrays into a DataSet.
    da_bld_count.raster.set_nodata(nodata=0)
    da_pop_count.raster.set_nodata(nodata=0)
    da_pop_bld_count.raster.set_nodata(nodata=0)
    ds_count = xr.merge(
        [
            da_bld_count.rename("bld"),
            da_pop_count.rename("pop"),
            da_pop_bld_count.rename("pop_bld"),
        ]
    )

    return ds_count


def get_area_grid(ds):
    """Returns a xarray.DataArray containing the area in [m2] of the reference grid ds.

    Parameters
    ----------
    ds : xarray.DataArray or xarray.DataSet
        xarray.DataArray or xarray.DataSet containing the reference grid(s).

    Returns
    -------
    da_area : xarray.DataArray
        xarray.DataArray containing the area in [m2] of the reference grid.
    """
    if ds.raster.crs.is_geographic:
        area = gis_utils.reggrid_area(
            ds.raster.ycoords.values, ds.raster.xcoords.values
        )
        da_area = xr.DataArray(
            data=area.astype("float32"), coords=ds.raster.coords, dims=ds.raster.dims
        )

    elif ds.raster.crs.is_projected:
        da = ds[list(ds.data_vars)[0]] if isinstance(ds, xr.Dataset) else ds
        xres = abs(da.raster.res[0]) * da.raster.crs.linear_units_factor[1]
        yres = abs(da.raster.res[1]) * da.raster.crs.linear_units_factor[1]
        da_area = xr.full_like(da, fill_value=1, dtype=np.float32) * xres * yres

    da_area.raster.set_nodata(0)
    da_area.raster.set_crs(ds.raster.crs)
    da_area.attrs.update(unit="m2")

    return da_area.rename("area")


def get_density_grid(ds):
    """Returns a xarray.DataArray or DataSet containing the density in [unit/m2] of the reference grid(s) ds.

    Parameters
    ----------
    ds: xarray.DataArray or xarray.DataSet
        xarray.DataArray or xarray.DataSet containing reference grid(s).

    Returns
    -------
    ds_out: xarray.DataArray or xarray.DataSet
        xarray.DataArray or xarray.DataSet containing the density in [unit/m2] of the reference grid(s).
    """

    # Create a grid that contains the area in m2 per grid cell.
    if ds.raster.crs.is_geographic:
        area = get_area_grid(ds)

    elif ds.raster.crs.is_projected:
        xres = abs(ds.raster.res[0]) * ds.raster.crs.linear_units_factor[1]
        yres = abs(ds.raster.res[1]) * ds.raster.crs.linear_units_factor[1]
        area = xres * yres

    # Create a grid that contains the density in unit/m2 per grid cell.
    ds_out = ds / area

    return ds_out


def get_grid_resolution(ds):
    """Returns a tuple containing the (average) (x, y) resolution in [m] of the reference grid ds.

    Parameters
    ----------
    ds: xarray.DataArray or xarray.DataSet
        xarray.DataArray or xarray.DataSet containing reference grid(s).

    Returns
    -------
    res_out: tuple
        Tuple containing the (x, y) resolution in [m] of the reference grid.
    """

    if ds.raster.crs.is_geographic:
        lat = np.mean(ds.raster.ycoords.values)
        x_res = ds.raster.res[0]
        y_res = ds.raster.res[1]
        res_out = gis_utils.cellres(lat, x_res, y_res)

    elif ds.raster.crs.is_projected:
        x_res = ds.raster.res[0] * ds.raster.crs.linear_units_factor[1]
        y_res = ds.raster.res[1] * ds.raster.crs.linear_units_factor[1]
        res_out = (x_res, y_res)

    return res_out
