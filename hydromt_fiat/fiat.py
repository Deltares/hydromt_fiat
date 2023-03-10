"""Implement fiat model class"""

from hydromt.models.model_api import Model
from hydromt_fiat.workflows.exposure_vector import ExposureVector
import logging
from pathlib import Path
from configparser import ConfigParser
import geopandas as gpd
import xarray as xr
import hydromt
from hydromt.cli.cli_utils import parse_config
from shutil import copy
from shapely.geometry import box


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
        self.set_geoms(geom, "region")

    def setup_config(self):
        # TODO: check if this is required
        NotImplemented

    def setup_exposure_vector(self, region):
        ev = ExposureVector(self.data_catalog, self.config["exposure"], region)
        ev.setup_from_single_source()

        # Add: linking damage functions to assets

    def setup_exposure_raster(self):
        NotImplemented

    def setup_vulnerability(self):
        NotImplemented

    def setup_hazard(self):
        NotImplemented

    def setup_social_vulnerability_index(self):
        NotImplemented

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

        # Set the paths.  # FIXME: how to do this more elegantly?
        config["hazard_dp"] = self.root.joinpath("hazard")
        config["exposure_dp"] = self.root.joinpath("exposure")
        config["vulnerability_dp"] = self.root.joinpath("vulnerability")
        config["output_dp"] = self.root.joinpath("output")

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
        config["exposure"] = opt["setup_exposure"]

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
        self._root = Path(root)

        # Set the paths.  # FIXME: how to do this more elegantly?
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

    def write(self):
        """Method to write the complete model schematization and configuration to file."""

        self.logger.info(f"Writing model data to {self.root}")
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
