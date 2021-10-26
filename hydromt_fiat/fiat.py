"""Implement fiat model class"""

from ast import literal_eval
from configparser import ConfigParser
from hydromt.cli.cli_utils import parse_config
from hydromt.models.model_api import Model
from os.path import join
from pathlib import Path
from shapely.geometry import box
from shutil import copy
import geopandas as gpd
import hydromt
import logging
import numpy as np
import pandas as pd
import xarray as xr

from . import workflows, DATADIR

__all__ = ["FiatModel"]

logger = logging.getLogger(__name__)


class FiatModel(Model):
    """General and basic API for the FIAT model in hydroMT."""

    _NAME = "fiat"
    _CONF = "fiat_configuration.ini"
    _GEOMS = {}  # FIXME Mapping from hydromt names to model specific names
    _MAPS = {}  # FIXME Mapping from hydromt names to model specific names
    _FOLDERS = ["hazard", "exposure", "susceptibility", "output"]
    _DATADIR = DATADIR

    def __init__(
        self,
        root=None,
        mode="w",
        config_fn=None,
        data_libs=None,
        logger=logger,
        deltares_data=False,
        artifact_data=False,
    ):
        super().__init__(
            root=root,
            mode=mode,
            config_fn=config_fn,
            data_libs=data_libs,
            deltares_data=deltares_data,
            artifact_data=artifact_data,
            logger=logger,
        )

    """ MODEL METHODS """

    def setup_basemaps(
        self,
        region,
        **kwargs,
    ):
        """Define the model domain that is used to clip the raster layers.

        Adds model layer:

        * **region** geom: A geometry with the nomenclature 'region'.

        Parameters
        ----------
        region: dict
            Dictionary describing region of interest, e.g. {'bbox': [xmin, ymin, xmax, ymax]}. See :py:meth:`~hydromt.workflows.parse_region()` for all options.
        """

        kind, region = hydromt.workflows.parse_region(region, logger=self.logger)
        if kind == "bbox":
            geom = gpd.GeoDataFrame(geometry=[box(*region["bbox"])], crs=4326)
        elif kind == "grid":
            geom = region["grid"].raster.box
        elif kind == "geom":
            geom = region["geom"]
        else:
            raise ValueError(
                f"Unknown region kind {kind} for FIAT, expected one of ['bbox', 'grid', 'geom']."
            )

        # Set the model region geometry (to be accessed through the shortcut self.region).
        self.set_staticgeoms(geom, "region")

    def setup_hazard(
        self,
        map_fn,
        map_type,
        chunks="auto",
        rp=None,
        crs=None,
        nodata=None,
        var=None,
        **kwargs,
    ):
        """Add a hazard map to the FIAT model schematization.

        Adds model layer:

        * **hazard** map(s): A raster map with the nomenclature <file_name>.

        Parameters
        ----------
        map_fn: (list of) str, Path
            Absolute or relative (with respect to the configuration file or hazard directory) path to the hazard file.
        map_type: (list of) str
            Description of the hazard type.
        rp: (list of) int, float, optional
            Return period in years, required for a risk calculation.
        crs: (list of) int, str, optional
            Coordinate reference system of the hazard file.
        nodata: (list of) int, float, optional
            Value that is assigned as nodata.
        var: (list of) str, optional
            Hazard variable name in NetCDF input files.
        chunks: (list of) int, optional
            Chunk sizes along each dimension used to load the hazard file into a dask array. The default is value 'auto'.
        """

        # Check the hazard input parameter types.
        map_fn_lst = [map_fn] if isinstance(map_fn, (str, Path)) else map_fn
        map_type_lst = [map_type] if isinstance(map_type, (str, Path)) else map_type
        self.check_param_type(map_fn_lst, name="map_fn", types=(str, Path))
        self.check_param_type(map_type_lst, name="map_type", types=str)
        if chunks != "auto":
            chunks_lst = [chunks] if isinstance(chunks, (int, dict)) else chunks
            self.check_param_type(chunks_lst, name="chunks", types=(int, dict))
            if not len(chunks_lst) == 1 or not len(chunks_lst) == len(map_fn_lst):
                raise IndexError(
                    "The number of 'chunks' parameters should match with the number of "
                    "'map_fn' parameters."
                )
        if rp is not None:
            rp_lst = [rp] if isinstance(rp, (int, float)) else rp
            self.check_param_type(rp_lst, name="rp", types=(float, int))
            if not len(rp_lst) == len(map_fn_lst):
                raise IndexError(
                    "The number of 'rp' parameters should match with the number of "
                    "'map_fn' parameters."
                )
        if crs is not None:
            crs_lst = [str(crs)] if isinstance(crs, (int, str)) else crs
            self.check_param_type(crs_lst, name="crs", types=(int, str))
        if nodata is not None:
            nodata_lst = [nodata] if isinstance(nodata, (float, int)) else nodata
            self.check_param_type(nodata_lst, name="nodata", types=(float, int))
        if var is not None:
            var_lst = [var] if isinstance(var, str) else var
            self.check_param_type(var_lst, name="var", types=str)

        # Check if the hazard input files exist.
        self.check_file_exist(map_fn_lst, name="map_fn")

        # Read the hazard map(s) and add to config and staticmaps.
        for idx, da_map_fn in enumerate(map_fn_lst):
            da_name = da_map_fn.stem
            da_type = self.get_param(
                map_type_lst, map_fn_lst, "hazard", da_name, idx, "map type"
            )

            # Get the local hazard map.
            kwargs.update(chunks=chunks if chunks == "auto" else chunks_lst[idx])
            if da_map_fn.suffix == ".nc":
                if var is None:
                    raise ValueError(
                        "The 'var' parameter is required when reading NetCDF data."
                    )
                kwargs.update(
                    variables=self.get_param(
                        var_lst, map_fn_lst, "hazard", da_name, idx, "NetCDF variable"
                    )
                )
            da = self.data_catalog.get_rasterdataset(
                da_map_fn, geom=self.region, **kwargs
            )

            # Set (if necessary) the coordinate reference system.
            if crs is not None and not da.raster.crs.is_epsg_code:
                da_crs = self.get_param(
                    crs_lst,
                    map_fn_lst,
                    "hazard",
                    da_name,
                    idx,
                    "coordinate reference system",
                )
                da_crs_str = da_crs if "EPSG" in da_crs else f"EPSG:{da_crs}"
                da.raster.set_crs(da_crs_str)
            elif crs is None and not da.raster.crs.is_epsg_code:
                raise ValueError(
                    "The hazard map has no coordinate reference system assigned."
                )

            # Set (if necessary) and mask the nodata value.
            if nodata is not None:
                da_nodata = self.get_param(
                    nodata_lst, map_fn_lst, "hazard", da_name, idx, "nodata"
                )
                da.raster.set_nodata(nodata=da_nodata)
            elif nodata is None and da.raster.nodata is None:
                raise ValueError("The hazard map has no nodata value assigned.")

            # Correct (if necessary) the grid orientation from the lower to the upper left corner.
            if da.raster.res[1] > 0:
                da = da.reindex({da.raster.y_dim: list(reversed(da.raster.ycoords))})

            # Check if the obtained hazard map is identical.
            if self.staticmaps and not self.staticmaps.raster.identical_grid(da):
                raise ValueError("The hazard maps should have identical grids.")

            # Get the return period input parameter.
            da_rp = (
                self.get_param(
                    rp_lst, map_fn_lst, "hazard", da_name, idx, "return period"
                )
                if "rp_lst" in locals()
                else None
            )
            if self.get_config("risk_output") and da_rp is None:

                # Get (if possible) the return period from dataset names if the input parameter is None.
                if "rp" in da_name.lower():
                    fstrip = lambda x: x in "0123456789."
                    rp_str = "".join(
                        filter(fstrip, da_name.lower().split("rp")[-1])
                    ).lstrip("0")
                    try:
                        assert isinstance(
                            literal_eval(rp_str) if rp_str else None, (int, float)
                        )
                        da_rp = literal_eval(rp_str)
                    except AssertionError:
                        raise ValueError(
                            f"Could not derive the return period for hazard map: {da_name}."
                        )
                else:
                    raise ValueError(
                        "The hazard map must contain a return period in order to conduct a risk calculation."
                    )

            # Add the hazard map to config and staticmaps.
            hazard_type = self.get_config("hazard_type", fallback="flooding")
            self.check_uniqueness(
                "hazard",
                da_type,
                da_name,
                {
                    "usage": True,
                    "map_fn": da_map_fn,
                    "map_type": da_type,
                    "rp": da_rp,
                    "crs": da.raster.crs,
                    "nodata": da.raster.nodata,
                    "var": None if "var_lst" not in locals() else var_lst[idx],
                    "chunks": "auto" if chunks == "auto" else chunks_lst[idx],
                },
                file_type="hazard",
                filename=da_name,
            )
            self.set_config(
                "hazard",
                da_type,
                da_name,
                {
                    "usage": "True",
                    "map_fn": da_map_fn,
                    "map_type": da_type,
                    "rp": da_rp,
                    "crs": da.raster.crs,
                    "nodata": da.raster.nodata,
                    "var": None if "var_lst" not in locals() else var_lst[idx],
                    "chunks": "auto" if chunks == "auto" else chunks_lst[idx],
                },
            )
            self.set_staticmaps(da, da_name)
            post = (
                f"(rp {da_rp})"
                if rp is not None and self.get_config("risk_output")
                else ""
            )
            self.logger.info(f"Added {hazard_type} hazard map: {da_name} {post}")

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
            ds_count = workflows.create_population_per_building_map(
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

    def setup_roads_value(
        self,
        exposure_fn,
        category,
        unit,
    ):
        # TODO general method to set exposure layer
        pass

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

    """ SUPPORT FUNCTIONS """

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
            if not tag in df_config["Alpha-3"].tolist():
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
        df_config = pd.read_excel(
            Path(self._DATADIR).joinpath("global_configuration.xlsx"),
            sheet_name="Buildings",
        )

        # TODO: Lookup country from shapefile!
        pass

    def get_param(self, param_lst, map_fn_lst, file_type, filename, i, param_name):
        """ """

        if len(param_lst) == 1:
            return param_lst[0]
        elif len(param_lst) != 1 and len(map_fn_lst) == len(param_lst):
            return param_lst[i]
        elif len(param_lst) != 1 and len(map_fn_lst) != len(param_lst):
            raise IndexError(
                f"Could not derive the {param_name} parameter for {file_type} "
                f"map: {filename}."
            )

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

    def get_susceptibility_function(self):
        """Return the susceptibility function id and the maximum damage number."""

        # Read the global exposure configuration.
        df_config = pd.read_excel(
            Path(self._DATADIR).joinpath("global_configuration.xlsx"),
            sheet_name="Buildings",
        )

        # Get the function id.
        sf_id = df_config.loc[
            df_config["Alpha-3"] == self.config["country"],
            f"Damage_Function_ID_{self.config['hazard_type'].capitalize()}",
        ].values[0]

        # Get the maximum damage value.
        max_damage = df_config.loc[
            df_config["Alpha-3"] == self.config["country"],
            f"Max_Damage_{self.config['hazard_type']. capitalize()}",
        ].values[0]

        return sf_id, max_damage

    def read(self):
        """Method to read the complete model schematization and configuration from file."""

        self.logger.info(f"Reading model data from {self.root}")
        self.read_config()
        self.read_staticmaps()
        self.read_staticgeoms()

    def read_forcing(self):
        """Read forcing at <root/?/> and parse to dict of xr.DataArray."""

        return self._forcing
        # raise NotImplementedError()

    def read_results(self):
        """Read results at <root/?/> and parse to dict of xr.DataArray."""

        return self._results
        # raise NotImplementedError()

    def read_states(self):
        """Read states at <root/?/> and parse to dict of xr.DataArray."""

        return self._states
        # raise NotImplementedError()

    def read_staticgeoms(self):
        """Read staticgeoms at <root/?/> and parse to dict of GeoPandas."""

        if not self._write:
            self._staticgeoms = dict()
        region_fn = Path(self.root).joinpath("region.GeoJSON")
        if region_fn.is_file():
            self.set_staticgeoms(gpd.read_file(region_fn), "region")

        return self._staticgeoms

    def read_staticmaps(self):
        """Read staticmaps at <root/?/> and parse to xarray Dataset."""

        if not self._write:
            self._staticmaps = xr.Dataset()

        # Read the hazard maps.
        for hazard_fn in [
            j["map_fn"]
            for i in self.get_config("hazard")
            for j in self.get_config("hazard", i).values()
        ]:
            if not hazard_fn.is_file():
                raise ValueError(f"Could not find the hazard map: {hazard_fn}.")
            else:
                self.set_staticmaps(
                    hydromt.open_raster(hazard_fn),
                    name=hazard_fn.stem,
                )

        # Read the exposure maps.
        for exposure_fn in [i["map_fn"] for i in self.get_config("exposure").values()]:
            if not exposure_fn.is_file():
                raise ValueError(f"Could not find the exposure map: {hazard_fn}.")
            else:
                self.set_staticmaps(
                    hydromt.open_raster(exposure_fn),
                    name=exposure_fn.stem,
                )

    def set_root(self, root=None, mode="w"):
        """Initialized the model root.
        In read mode it checks if the root exists.
        In write mode in creates the required model folder structure.

        Parameters
        ----------
        root: str, optional
            Path to model root.
        mode: {"r", "r+", "w"}, optional
            Read/write-only mode for model files.
        """

        # Do super method and update absolute paths in config.
        if root is None:
            root = Path(self._config_fn).parent
        super().set_root(root=root, mode=mode)
        if self._write and root is not None:
            self._root = Path(root)

            # Set the general information.
            self.set_config("hazard_dp", self.root.joinpath("hazard"))
            self.set_config("exposure_dp", self.root.joinpath("exposure"))
            self.set_config("susceptibility_dp", self.root.joinpath("susceptibility"))
            self.set_config("output_dp", self.root.joinpath("output"))

            # Set the hazard information.
            if self.get_config("hazard"):
                for hazard_type, hazard_scenario in self.get_config("hazard").items():
                    for hazard_fn in hazard_scenario:
                        hazard_scenario[hazard_fn]["map_fn"] = self.root.joinpath(
                            hazard_scenario[hazard_fn]["map_fn"].name,
                        )
                        self.set_config(
                            "hazard",
                            hazard_type,
                            hazard_fn,
                            hazard_scenario[hazard_fn],
                        )
            if self.get_config("exposure"):
                for exposure_fn in self.get_config("exposure"):
                    self.set_config(
                        "exposure",
                        exposure_fn,
                        "map_fn",
                        self.root.joinpath(
                            self.get_config("exposure", exposure_fn, "map_fn").name,
                        ),
                    )

    def write(self):
        """Method to write the complete model schematization and configuration to file."""

        self.logger.info(f"Writing model data to {self.root}")
        # if in r, r+ mode, only write updated components
        if not self._write:
            self.logger.warning("Cannot write in read-only mode")
            return
        if self.config:  # try to read default if not yet set
            self.write_config()
        if self._staticmaps:
            self.write_staticmaps()
        if self._staticgeoms:
            self.write_staticgeoms()
        if self._forcing:
            self.write_forcing()

    def write_forcing(self):
        """write forcing at <root/?/> in model ready format."""

        pass
        # raise NotImplementedError()

    def write_results(self):
        """write results at <root/?/> in model ready format."""

        pass
        # raise NotImplementedError()

    def write_states(self):
        """write states at <root/?/> in model ready format."""

        pass
        # raise NotImplementedError()

    def write_staticgeoms(self):
        """Write staticmaps at <root/?/> in model ready format."""

        if not self._write:
            raise IOError("Model opened in read-only mode")
        if self._staticgeoms:
            for name, gdf in self._staticgeoms.items():
                gdf.to_file(join(self.root, f"{name}.geojson"), driver="GeoJSON")

    def write_staticmaps(self, compress="lzw"):
        """Write staticmaps at <root/?/> in model ready format."""

        # to write to gdal raster files use: self.staticmaps.raster.to_mapstack()
        # to write to netcdf use: self.staticmaps.to_netcdf()
        if not self._write:
            raise IOError("Model opened in read-only mode.")
        hazard_maps = [
            j for i in self.get_config("hazard") for j in self.get_config("hazard", i)
        ]
        if len(hazard_maps) > 0:
            self.staticmaps[hazard_maps].raster.to_mapstack(
                self.get_config("hazard_dp"), compress=compress
            )
        exposure_maps = [i for i in self.staticmaps.data_vars if i not in hazard_maps]
        if len(exposure_maps) > 0:
            self.staticmaps[exposure_maps].raster.to_mapstack(
                self.get_config("exposure_dp"), compress=compress
            )

    def _configread(self, fn):
        """Parse fiat_configuration.ini to dict."""

        # Read and parse the fiat_configuration.ini.
        opt = parse_config(fn)

        # Store the general information.
        config = opt["setup_config"]

        # Store the hazard information.
        config["hazard"] = {}
        for hazard_dict in [opt[key] for key in opt.keys() if "hazard" in key]:
            hazard_dict.update(
                {"map_fn": config["hazard_dp"].joinpath(hazard_dict["map_fn"])}
            )
            if not hazard_dict["map_type"] in config["hazard"].keys():
                config["hazard"][hazard_dict["map_type"]] = {
                    hazard_dict["map_fn"].stem: hazard_dict,
                }
            else:
                config["hazard"][hazard_dict["map_type"]].update(
                    {
                        hazard_dict["map_fn"].stem: hazard_dict,
                    }
                )

        # Store the exposure information.
        config["exposure"] = {}
        for exposure_dict in [opt[key] for key in opt.keys() if "exposure" in key]:
            exposure_dict.update(
                {"map_fn": config["exposure_dp"].joinpath(exposure_dict["map_fn"])}
            )
            config["exposure"].update(
                {
                    exposure_dict["map_fn"].stem: exposure_dict,
                }
            )

        return config

    def _configwrite(self, fn):
        """Write config to fiat_configuration.ini"""

        parser = ConfigParser()

        # Store the general information.
        parser["setup_config"] = {
            "case": str(self.config.get("case")),
            "strategy": str(self.config.get("strategy")),
            "scenario": str(self.config.get("scenario")),
            "year": str(self.config.get("year")),
            "country": str(self.get_config("country")),
            "hazard_type": str(self.config.get("hazard_type")),
            "output_unit": str(self.config.get("output_unit")),
            "hazard_dp": str(self.config.get("hazard_dp").name),
            "exposure_dp": str(self.config.get("exposure_dp").name),
            "susceptibility_dp": str(self.config.get("susceptibility_dp").name),
            "output_dp": str(self.config.get("output_dp").name),
            "category_output": str(self.config.get("category_output")),
            "total_output": str(self.config.get("total_output")),
            "risk_output": str(self.config.get("risk_output")),
            "map_output": str(self.config.get("map_output")),
        }

        # Store the hazard information.
        for idx, hazard_scenario in enumerate(
            [
                (i, j)
                for i in self.get_config("hazard")
                for j in self.get_config("hazard", i)
            ]
        ):
            section_name = f"setup_hazard{idx + 1}"
            parser.add_section(section_name)
            for hazard_key in self.get_config(
                "hazard", hazard_scenario[0], hazard_scenario[1]
            ):
                if hazard_key == "map_fn":
                    parser.set(
                        section_name,
                        hazard_key,
                        str(
                            self.get_config(
                                "hazard",
                                hazard_scenario[0],
                                hazard_scenario[1],
                                hazard_key,
                            ).name
                        ),
                    )
                else:
                    parser.set(
                        section_name,
                        hazard_key,
                        str(
                            self.get_config(
                                "hazard",
                                hazard_scenario[0],
                                hazard_scenario[1],
                                hazard_key,
                            )
                        ),
                    )

        # Store the exposure information.
        for idx, exposure_fn in enumerate(self.get_config("exposure")):
            section_name = f"setup_exposure{idx + 1}"
            parser.add_section(section_name)
            for exposure_key in self.get_config("exposure", exposure_fn):
                if exposure_key == "map_fn":
                    parser.set(
                        section_name,
                        exposure_key,
                        str(self.get_config("exposure", exposure_fn, exposure_key).name),
                    )
                elif exposure_key == "function_fn":
                    parser.set(
                        section_name,
                        exposure_key,
                        str({
                            i: j.name for i, j in self.get_config(
                                "exposure",
                                exposure_fn,
                                exposure_key,
                            ).items()
                        }),
                    )
                    for function_key in self.get_config(
                            "exposure",
                            exposure_fn,
                            exposure_key,
                    ):
                        sf_path = self.get_config(
                            "exposure",
                            exposure_fn,
                            exposure_key,
                        )[function_key]
                        copy(
                            sf_path,
                            self.get_config("susceptibility_dp").joinpath(sf_path.name),
                        )
                else:
                    parser.set(
                        section_name,
                        exposure_key,
                        str(self.get_config("exposure", exposure_fn, exposure_key)),
                    )

        # Save the configuration file.
        with open(self.root.joinpath(self._CONF), "w") as config:
            parser.write(config)

    """ CONTROL FUNCTIONS """

    def check_dir_exist(self, dir, name=None):
        """ """

        if not isinstance(dir, Path):
            raise TypeError(
                f"The directory indicated by the '{name}' parameter does not exist."
            )

    def check_file_exist(self, param_lst, name=None, input_dir=None):
        """ """

        for param_idx, param in enumerate(param_lst):
            if isinstance(param, dict):
                fn_lst = list(param.values())
            else:
                fn_lst = [param]
            for fn_idx, fn in enumerate(fn_lst):
                if not Path(fn).is_file():
                    if self.root.joinpath(fn).is_file():
                        if isinstance(param, dict):
                            param_lst[param_idx][
                                list(param.keys())[fn_idx]
                            ] = self.root.joinpath(fn)
                        else:
                            param_lst[param_idx] = self.root.joinpath(fn)
                    if input_dir is not None:
                        if self.get_config(input_dir).joinpath(fn).is_file():
                            if isinstance(param, dict):
                                param_lst[param_idx][
                                    list(param.keys())[fn_idx]
                                ] = self.get_config(input_dir).joinpath(fn)
                            else:
                                param_lst[param_idx] = self.get_config(
                                    input_dir
                                ).joinpath(fn)
                else:
                    if isinstance(param, dict):
                        param_lst[param_idx][list(param.keys())[fn_idx]] = Path(fn)
                    else:
                        param_lst[param_idx] = Path(fn)
                try:
                    if isinstance(param, dict):
                        assert isinstance(
                            param_lst[param_idx][list(param.keys())[fn_idx]], Path
                        )
                    else:
                        assert isinstance(param_lst[param_idx], Path)
                except AssertionError:
                    if input_dir is None:
                        raise TypeError(
                            f"The file indicated by the '{name}' parameter does not"
                            f" exist in the directory '{self.root}'."
                        )
                    else:
                        raise TypeError(
                            f"The file indicated by the '{name}' parameter does not"
                            f" exist in either of the directories '{self.root}' or "
                            f"'{self.get_config(input_dir)}'."
                        )

    def check_param_type(self, param, name=None, types=None):
        """ """

        if not isinstance(param, list):
            raise TypeError(
                f"The '{name}_lst' parameter should be a of {list}, received a "
                f"{type(param)} instead."
            )
        for i in param:
            if not isinstance(i, types):
                if isinstance(types, tuple):
                    types = " or ".join([str(j) for j in types])
                else:
                    types = types
                raise TypeError(
                    f"The '{name}' parameter should be a of {types}, received a "
                    f"{type(i)} instead."
                )

    def check_uniqueness(self, *args, file_type=None, filename=None):
        """ """

        args = list(args)
        if len(args) == 1 and "." in args[0]:
            args = args[0].split(".") + args[1:]
        branch = args.pop(-1)
        for key in args[::-1]:
            branch = {key: branch}

        if self.get_config(args[0], args[1]):
            for key in self.staticmaps.data_vars:
                if filename == key:
                    raise ValueError(
                        f"The filenames of the {file_type} maps should be unique."
                    )
                if (
                    self.get_config(args[0], args[1], key)
                    == list(branch[args[0]][args[1]].values())[0]
                ):
                    raise ValueError(f"Each model input layers must be unique.")
