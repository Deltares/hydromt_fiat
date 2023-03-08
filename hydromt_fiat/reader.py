import geopandas as gpd
from pathlib import Path
import xarray as xr
import hydromt
from hydromt.cli.cli_utils import parse_config


### TO BE UPDATED ###
class Reader:
    def __init__(self):
        """Method to read the complete model schematization and configuration from file."""

        self.logger.info(f"Reading model data from {self.root}")

    def read_config(self, fn):
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
                        i: config["susceptibility_dp"].joinpath(j)
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
