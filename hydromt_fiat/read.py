import geopandas as gpd
from pathlib import Path
import xarray as xr
import hydromt


### TO BE UPDATED ###
class Read:
    def __init__(self):
        """Method to read the complete model schematization and configuration from file."""

        self.logger.info(f"Reading model data from {self.root}")
        self.read_config()
        self.read_staticmaps()
        self.read_staticgeoms()

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