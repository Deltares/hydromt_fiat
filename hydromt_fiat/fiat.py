"""Implement fiat model class"""

from hydromt.models.model_api import Model
import logging
from pathlib import Path
from configparser import ConfigParser
import geopandas as gpd
import xarray as xr
import hydromt
from hydromt.cli.cli_utils import parse_config
from shutil import copy
from hydromt_fiat.workflows.social_vulnerability_index import SocialVulnerabilityIndex


from . import DATADIR

__all__ = ["FiatModel"]

_logger = logging.getLogger(__name__)


class FiatModel(Model):
    """General and basic API for the FIAT model in hydroMT."""

    _NAME = "fiat"
    _CONF = "fiat_configuration.ini"
    _GEOMS = {}  # FIXME Mapping from hydromt names to model specific names
    _MAPS = {}  # FIXME Mapping from hydromt names to model specific names
    _FOLDERS = ["hazard", "exposure", "vulnerability", "output"]
    _DATADIR = DATADIR

    def __init__(
        self,
        root=None,
        mode="w",
        config_fn=None,
        data_libs=None,
        logger=_logger,
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

    def setup_config(self):
        # TODO: check if this is required
        NotImplemented

    def setup_exposure_vector(self, region, **kwargs):
        NotImplemented
        # workflows.exposure_vector.Exposure

    def setup_exposure_raster(self):
        NotImplemented

    def setup_vulnerability(self):
        NotImplemented

    def setup_hazard(self):
        NotImplemented

    def setup_social_vulnerability_index(self, census_key: str, path:str, state_abbreviation:str):

        #Create SVI object 
        svi = SocialVulnerabilityIndex(self.data_catalog, self.config)

        #Call functionalities of SVI
        svi.set_up_census_key(census_key)
        svi.variable_code_csv_to_pd_df(path)
        svi.set_up_download_codes()
        svi.set_up_state_code(state_abbreviation)
        svi.download_census_data()
        svi.rename_census_data("Census_code_withE", "Census_variable_name")
        svi.create_indicator_groups("Census_variable_name", "Indicator_code")
        svi.processing_svi_data()
        svi.normalization_svi_data()
        svi.domain_scores()
        svi.composite_scores()

#TO DO: JOIN WITH GEOMETRIES. FOR MAPPING. 
#this link can be used: https://github.com/datamade/census

    def read(self):
        """Method to read the complete model schematization and configuration from file."""
        self.logger.info(f"Reading model data from {self.root}")
        self.read_config()
        self.read_staticmaps()
        self.read_staticgeoms()

    def _configread(self, fn):
        """Parse fiat_configuration.ini to dict."""

        # Read and parse the fiat_configuration.ini.
        opt = parse_config(fn)

        # Store the general information.
        config = opt["setup_config"]

        # Set the paths
        config["hazard_dp"] = Path(self.root).joinpath("hazard")
        config["exposure_dp"] = Path(self.root).joinpath("exposure")
        config["vulnerability_dp"] = Path(self.root).joinpath("vulnerability")
        config["output_dp"] = Path(self.root).joinpath("output")

        # Store the hazard information.
        config["hazard"] = {}
        for hazard_dict in [opt[key] for key in opt.keys() if "hazard" in key]:
            hazard_dict.update(
                {"map_fn": config["hazard_dp"].joinpath(hazard_dict["map_fn"])}
            )
            if hazard_dict["map_type"] not in config["hazard"].keys():
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
            exposure_dict.update(
                {
                    "function_fn": {
                        i: config["vulnerability_dp"].joinpath(j)
                        for i, j in exposure_dict["function_fn"].items()
                    }
                }
            )
            config["exposure"].update(
                {
                    exposure_dict["map_fn"].stem: exposure_dict,
                }
            )

        return config

    def read_staticgeoms(self):
        """Read staticgeoms at <root/?/> and parse to dict of GeoPandas."""

        if not self._write:
            self._staticgeoms = dict()
        region_fn = Path(self.root).joinpath("region.GeoJSON")
        if region_fn.is_file():
            self.set_geoms(gpd.read_file(region_fn), "region")

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
            self.set_config("vulnerability_dp", self.root.joinpath("vulnerability"))
            self.set_config("output_dp", self.root.joinpath("output"))

            # Set the hazard information.
            if self.get_config("hazard"):
                for hazard_type, hazard_scenario in self.get_config("hazard").items():
                    for hazard_fn in hazard_scenario:
                        hazard_scenario[hazard_fn]["map_fn"] = self.get_config(
                            "hazard_dp"
                        ).joinpath(hazard_scenario[hazard_fn]["map_fn"].name)
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
                        self.get_config("exposure_dp").joinpath(
                            self.get_config("exposure", exposure_fn, "map_fn").name,
                        ),
                    )
                    for sf_path in self.get_config(
                        "exposure",
                        exposure_fn,
                        "function_fn",
                    ).values():
                        if (
                            not self.get_config("vulnerability_dp")
                            .joinpath(
                                sf_path.name,
                            )
                            .is_file()
                        ):
                            copy(
                                sf_path,
                                self.get_config("vulnerability_dp").joinpath(
                                    sf_path.name,
                                ),
                            )
                    self.set_config(
                        "exposure",
                        exposure_fn,
                        "function_fn",
                        {
                            i: self.get_config("vulnerability_dp").joinpath(j.name)
                            for i, j in self.get_config(
                                "exposure",
                                exposure_fn,
                                "function_fn",
                            ).items()
                        },
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

    def write_staticgeoms(self):
        """Write staticmaps at <root/?/> in model ready format."""

        if not self._write:
            raise IOError("Model opened in read-only mode")
        if self._staticgeoms:
            for name, gdf in self._staticgeoms.items():
                gdf.to_file(
                    Path(self.root).joinpath(f"{name}.geojson"), driver="GeoJSON"
                )

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
            "vulnerability_dp": str(self.config.get("vulnerability_dp").name),
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
                        str(
                            self.get_config("exposure", exposure_fn, exposure_key).name
                        ),
                    )
                elif exposure_key == "function_fn":
                    parser.set(
                        section_name,
                        exposure_key,
                        str(
                            {
                                i: j.name
                                for i, j in self.get_config(
                                    "exposure",
                                    exposure_fn,
                                    exposure_key,
                                ).items()
                            }
                        ),
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
                        if (
                            not self.get_config("vulnerability_dp")
                            .joinpath(
                                sf_path.name,
                            )
                            .is_file()
                        ):
                            copy(
                                sf_path,
                                self.get_config("vulnerability_dp").joinpath(
                                    sf_path.name,
                                ),
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
