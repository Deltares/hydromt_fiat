import logging
from pathlib import Path


### TO BE UPDATED ###
class Write:
    def __init__(self):
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

    def write_staticgeoms(self):
        """Write staticmaps at <root/?/> in model ready format."""

        if not self._write:
            raise IOError("Model opened in read-only mode")
        if self._staticgeoms:
            for name, gdf in self._staticgeoms.items():
                gdf.to_file(Path(self.root).joinpath(f"{name}.geojson"), driver="GeoJSON")

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

