from hydromt_fiat.workflows.exposure import Exposure
from hydromt import gis_utils, raster
import logging
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path

logger = logging.getLogger(__name__)


### TO BE UPDATED ###
class ExposureRaster(Exposure):
    def setup_buildings_value(
        self,
        bld_fn="wsf_bld_2015",
        pop_fn="ghs_pop_2015",
        chunks="auto",
        unit="USD",
        scale_factor=1,
        weight_factor=1,
        function_fn=None,
        country=None,
        **kwargs,
    ):
        """Add a buildings value exposure map to the FIAT model schematization.

        Adds model layer:

        * **exposure** map: A raster map with the nomenclature 'buildings_value'.

        Parameters
        ----------
        bld_fn: str
            Name tag of or absolute or relative (with respect to the configuration file) path to the building footprint file. The default value is 'wsf_bld_2015'.
        pop_fn: str
            Name tag of or absolute or relative (with respect to the configuration file) path to the population count file. The default value is 'ghs_pop_2015'.
        chunks: int, optional
            Chunk sizes along each dimension used to load the building footprint and population count files into a dask arrays. The default value is 'auto'.
        function_fn: dict, optional
            Absolute or relative (with respect to the configuration file or susceptibility directory) path to the susceptibility file. The default value is the JCR continental susceptibilty function (https://publications.jrc.ec.europa.eu/repository/handle/JRC105688) related to the country parameter.
        scale_factor: int, float, optional
            Scaling factor of the exposure values. The default value is 1.
        weight_factor: int, float, optional
            Weight factor of the exposure values in the total damage and risk results. The default value is 1.
        """

        if bld_fn and pop_fn:
            kwargs.update(chunks=chunks)

            # TODO: Make sure that the kwargs of layers in the .ylm can be overwritten!

            # Clip the building footprint map from the global dataset and store as a xarray.DataArray.
            da_bld = self.data_catalog.get_rasterdataset(
                bld_fn,
                geom=self.region,
                buffer=4,
                **kwargs,
            ).rename("bld")

            # Clip the population map from the global dataset and store as a xarray.DataArray.
            da_pop = self.data_catalog.get_rasterdataset(
                pop_fn,
                geom=self.region,
                buffer=4,
                **kwargs,
            ).rename("pop")

            # TODO: Make sure that the create_population_per_building_map is memory proof!

            # Create the population, buildings and population per building count maps and store as a xarray.DataSet.
            ds_count = create_population_per_building_map(
                da_bld,
                da_pop,
                ds_like=self.staticmaps,
                logger=self.logger,
            )

            # Add the exposure count maps to staticmaps.
            self.set_staticmaps(ds_count["bld"], name="buildings_count")
            self.set_staticmaps(ds_count["pop"], name="population_count")
            self.set_staticmaps(ds_count["pop_bld"], name="population_buildings_count")

        if "population_buildings_count" in self.staticmaps.data_vars:
            # Get the associated country tag (alpha-3 code).
            tag = self.get_country_tag(country)

            # Get the associated susceptibility information (function id and maximum damage value).
            sf_id, max_damage = self.get_susceptibility_function()
            self.logger.debug(
                "Calculating building values with maximum damage: "
                f"{max_damage:.2f} {unit:s}/person (country = {tag:s})."
            )
            if not function_fn:
                sf_path = Path(self._DATADIR).joinpath(
                    "damage_functions",
                    self.get_config("hazard_type"),
                    self.get_config("hazard_unit"),
                    f"{sf_id}.csv",
                )
            else:
                self.check_file_exist([function_fn], name="sf_path")
                sf_path = list(function_fn.values())[0]

            # Create a building value map.
            ds_bld_value = self.staticmaps["population_buildings_count"] * max_damage
            ds_bld_value.raster.set_nodata(nodata=0)
            ds_bld_value.name = "bld_value"

        # Check if the buildings value map has correctly been generated.
        else:
            raise ValueError(
                "The buildings value exposure layer is not correctly generated."
            )

        # Add the buildings value map to config and staticmaps.
        map_name = "buildings_value"
        self.check_uniqueness(
            "exposure",
            map_name,
            {
                "usage": True,
                "map_fn": self.get_config("exposure_dp").joinpath(
                    "buildings_value.tif"
                ),
                "category": map_name,
                "subcategory": None,
                "unit": unit,
                "crs": ds_bld_value.raster.crs,
                "nodata": ds_bld_value.raster.nodata,
                "chunks": chunks,
                "function_fn": {
                    "water_depth"
                    if not function_fn
                    else list(function_fn.keys())[0]: sf_path
                },
                "comp_alg": "max",
                "scale_factor": scale_factor,
                "weight_factor": weight_factor,
            },
            file_type="exposure",
            filename=map_name,
        )
        self.set_config(
            "exposure",
            map_name,
            {
                "usage": True,
                "map_fn": self.get_config("exposure_dp").joinpath(
                    "buildings_value.tif"
                ),
                "category": map_name,
                "subcategory": None,
                "unit": unit,
                "crs": ds_bld_value.raster.crs,
                "nodata": ds_bld_value.raster.nodata,
                "chunks": chunks,
                "function_fn": {
                    "water_depth"
                    if not function_fn
                    else list(function_fn.keys())[0]: sf_path
                },
                "comp_alg": "max",
                "scale_factor": scale_factor,
                "weight_factor": weight_factor,
            },
        )
        self.set_staticmaps(ds_bld_value, map_name)
        self.logger.info("Added exposure map: buildings value")

    def scale_exposure(
        self,
        scenario,
        year,
        ref_year=2015,
    ):
        """Scale the exposure to the forecast year, using the shared socioeconomic pathway (SSP) projections for population and GDP growth.

        Parameters
        ----------
        scenario: str
            Name tag of the shared socioeconomic pathway (SSP), required for a forecast calculation.
        year: int
            The forecast year to which the exposure data is scaled.
        ref_year: int, optional
            The reference year from which the population originates. The default value is 2015 (related to the default 'ghs_pop_2015' population layer).
        """

        # Set the scenario and year config parameters.
        self.set_config("scenario", scenario)
        self.set_config("year", year)

        # Determine the scale factor.
        pop_correction = self.get_population_correction_factor(ref_year)
        gdp_correction = self.get_gdp_correction_factor()
        scale_factor = pop_correction * gdp_correction

        # Set the scale factor.
        for exposure_fn in self.get_config("exposure"):
            self.set_config(
                "exposure",
                exposure_fn,
                "scale_factor",
                scale_factor,
            )

        def get_country_tag(self, country):
            """Return the country tag for a country name input."""
            # Get the country tag from the country name.
            if country or "country" in self.config:
                if not country:
                    country = self.config["country"]

                # Read the global exposure configuration.
                df_config = pd.read_excel(
                    Path(self._DATADIR).joinpath("global_configuration.xlsx"),
                    sheet_name="Buildings",
                )

                # Extract the country tag.
                if len(country) > 3:
                    tag = (
                        df_config.loc[
                            df_config["Country_Name"] == country, "Alpha-3"
                        ].values[0]
                        if country in df_config["Country_Name"].tolist()
                        else None
                    )
                else:
                    tag = country

                # If the country tag is not valid, get the country tag from nearest country.
                if tag not in df_config["Alpha-3"].tolist():
                    tag = self.get_nearest_country()
                    self.logger.debug(
                        "The country tag (related to the country name) is not valid."
                        "The country tag of the nearest country is used instead."
                    )

            # Set the country tag.
            self.set_config("country", tag)
            return tag

    def get_gdp_correction_factor(self):
        """ """

        # Read the global SSP data.
        df_pop = pd.read_excel(
            Path(self._DATADIR).joinpath("growth_scenarios", "global_pop.xlsx"),
            sheet_name="Data",
        )
        df_gdp = pd.read_excel(
            Path(self._DATADIR).joinpath("growth_scenarios", "global_gdp(ppp).xlsx"),
            sheet_name="Data",
        )

        # Extract the national data.
        pop_data = (
            df_pop.loc[
                (df_pop["Region"] == self.config["country"])
                & (df_pop["Scenario"] == self.config["scenario"])
            ]
            .reset_index(drop=True)
            .iloc[:, 5:-1]
        )
        gdp_data = (
            df_gdp.loc[
                (df_gdp["Region"] == self.config["country"])
                & (df_gdp["Scenario"] == self.config["scenario"])
            ]
            .reset_index(drop=True)
            .iloc[:, 5:-1]
        )

        # In case multiple data sources are available, use the averaged values.
        pop_data = pop_data.mean(axis=0)
        gdp_data = gdp_data.mean(axis=0)

        # Determine the GDP(PPP) per capita and interpolate (linear) the data to obtain annual results.
        gdp_ppp_data = gdp_data * 1000 / pop_data
        annual_gdp_per_cap_data = np.array(
            range(int(gdp_ppp_data.index[0]), int(gdp_ppp_data.index[-1]) + 1, 1)
        )
        interp_gdp_per_cap_data = list(
            np.interp(
                annual_gdp_per_cap_data,
                gdp_ppp_data.index.astype(int).values,
                gdp_ppp_data.values.astype(float),
            )
        )

        # Determine the indexes of the reference year (2019) and the forecast year.
        ref_year_idx = list(annual_gdp_per_cap_data).index(2019)
        forecast_year_idx = list(annual_gdp_per_cap_data).index(self.config["year"])

        # Calculate the correction factor.
        correction_factor = (
            interp_gdp_per_cap_data[forecast_year_idx]
            / interp_gdp_per_cap_data[ref_year_idx]
        )

        return correction_factor

    def get_nearest_country(self):
        """Return the country tag of the nearest country."""

        # Read the global exposure configuration.
        pd.read_excel(
            Path(self._DATADIR).joinpath("global_configuration.xlsx"),
            sheet_name="Buildings",
        )

        # TODO: Lookup country from shapefile!
        pass

    def get_population_correction_factor(self, ref_year):
        """ """

        # Read the global SSP data.
        df_pop = pd.read_excel(
            Path(self._DATADIR).joinpath("growth_scenarios", "global_pop.xlsx"),
            sheet_name="Data",
        )

        # Extract the national data.
        pop_data = (
            df_pop.loc[
                (df_pop["Region"] == self.config["country"])
                & (df_pop["Scenario"] == self.config["scenario"])
            ]
            .reset_index(drop=True)
            .iloc[:, 5:-1]
        )

        # In case multiple data sources are available, use the averaged values.
        pop_data = pop_data.mean(axis=0)

        # Interpolate (linear) the data to obtain annual results.
        annual_pop_data = np.array(
            range(int(pop_data.index[0]), int(pop_data.index[-1]) + 1, 1)
        )
        interp_pop_data = list(
            np.interp(
                annual_pop_data,
                pop_data.index.astype(int).values,
                pop_data.values.astype(float),
            )
        )

        # Determine the indexes of the reference year (2015) and the forecast year.

        # TODO: Check if the population map is the default layer (ghs_pop_2015), otherwise give warning that the reference does not relate to the layer!

        ref_year_idx = list(annual_pop_data).index(ref_year)
        forecast_year_idx = list(annual_pop_data).index(self.config["year"])

        # Calculate the correction factor.
        pop_correction = (
            interp_pop_data[forecast_year_idx] / interp_pop_data[ref_year_idx]
        )

        return pop_correction


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
            xr.merge(
                [
                    da_bld.reset_coords(drop=True),
                    da_bld_area.reset_coords(drop=True),
                    da_idx.reset_coords(drop=True),
                ]
            )
            .stack(yx=(y_dim, x_dim))  # flatten to make dataframe
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
        da_pop_count = (
            da_pop_density.raster.reproject_like(ds_like, method="average")
            * da_like_area
        )
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
        da_pop_bld_count = da_bld_count.where(da_bld_count == 0, other=da_pop_count)

    # Correction!!
    da_pop_bld_count = (
        da_pop_bld_count * np.sum(da_pop_count) / np.sum(da_pop_bld_count)
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
