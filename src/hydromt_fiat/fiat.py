"""Main module."""

import logging
from pathlib import Path
from typing import List, Union

import geopandas as gpd
import xarray as xr
from hydromt.model import Model
from hydromt.model.components import (
    ConfigComponent,
    GeomsComponent,
    GridComponent,
    TablesComponent,
)
from hydromt.model.steps import hydromt_step

from hydromt_fiat.components import RegionComponent

# Set some global variables
__all__ = ["FIATModel"]
__hydromt_eps__ = ["FIATModel"]  # core entrypoints

# Create a logger
logger = logging.getLogger(__name__)


class FIATModel(Model):
    """Read or Write a FIAT model.

    Parameters
    ----------
    root : str, optional
        Model root, by default None
    mode : {'r','r+','w'}, optional
        read/append/write mode, by default "w"
    data_libs : List[str], optional
        List of data catalog configuration files, by default None
    logger:
        The logger to be used.
    **catalog_keys:
        Additional keyword arguments to be passed down to the DataCatalog.
    """

    name: str = "fiat_model"
    # supported model version should be filled by the plugins
    # e.g. _MODEL_VERSION = ">=1.0, <1.1"
    _MODEL_VERSION = None

    def __init__(
        self,
        root: str | None = None,
        mode: str = "r",
        data_libs: Union[List, str] | None = None,
        **catalog_keys,
    ):
        Model.__init__(
            self,
            root,
            components={"region": RegionComponent(model=self)},
            mode=mode,
            region_component="region",
            data_libs=data_libs,
            **catalog_keys,
        )

        ## Setup components
        self.add_component(
            "config",
            ConfigComponent(model=self, filename="settings.toml"),
        )
        self.add_component("exposure_data", TablesComponent(model=self))
        self.add_component(
            "exposure_geoms",
            GeomsComponent(model=self, region_component="region"),
        )
        self.add_component(
            "exposure_grid",
            GridComponent(model=self, region_component="region"),
        )
        self.add_component(
            "hazard_grid",
            GridComponent(
                model=self, region_component="region", filename="hazard_grid.nc"
            ),
        )
        self.add_component("vulnerability_data", TablesComponent(model=self))

    ## Properties
    @property
    def config(self):
        """Return the configurations component."""
        return self.components["config"]

    ## I/O
    @hydromt_step
    def read(self):
        """Read the FIAT model."""
        Model.read(self)

    @hydromt_step
    def write(self):
        """Write the FIAT model."""
        Model.write(self)

    ## Setup methods
    @hydromt_step
    def setup_config(
        self,
        **settings: dict,
    ):
        """Set config file entries.

        settings : dict
            Settings for the configuration provided as keyword arguments
            (KEY=VALUE).
        """
        for key, value in settings.items():
            self.config.set(key, value)

    @hydromt_step
    def setup_region(
        self,
        region: Path | str,
    ):
        """Set the region of the FIAT model.

        Parameters
        ----------
        region : Path | str
            Path to the region vector file.
        """
        region = Path(region)
        if not region.is_file():
            raise FileNotFoundError(region.as_posix())
        geom = gpd.read_file(region)
        self.components["region"].set(geom, "region")

    @hydromt_step
    def setup_exposure(
        self,
        exposure_fname: Path | str,
    ):
        """Set up the exposure from a data source.

        Parameters
        ----------
        exposure_fname : Path | str
            _description_
        """
        pass

    @hydromt_step
    def setup_hazard(
        self,
        hazard_fnames: Path | str | list[Path | str],
        risk: bool = False,
        return_periods: list[int] | None = None,
        hazard_type: str | None = "flooding",
    ):
        """Set up hazard maps."""
        if not isinstance(hazard_fnames, list):
            hazard_fnames = [hazard_fnames]
        if risk and not return_periods:
            raise ValueError("Cannot perform risk analysis without return periods")
        if risk and len(return_periods) != len(hazard_fnames):
            raise ValueError("Return periods do not match the number of hazard files")

        # Get components from model
        grid = self.get_component("hazard_grid")

        # Check if there is already data set to this grid component. This will cause
        # problems with setting attrs
        if not grid.data.sizes == {}:
            raise ValueError("Cannot set hazard data on existing hazard grid data.")

        hazard_dataarrays = []
        for i, hazard_file in enumerate(hazard_fnames):
            da = self.data_catalog.get_rasterdataset(hazard_file)

            # Convert to gdal compliant
            da.encoding["_FillValue"] = None
            da: xr.DataArray = da.raster.gdal_compliant()

            # ensure variable name is lowercase
            da_name = Path(hazard_file).stem.lower()
            da = da.rename(da_name)

            # Check if map is rotated and if yes, reproject to a non-rotated grid
            if "xc" in da.coords:
                self.logger.warning(
                    "Hazard map is rotated. It will be reprojected"
                    " to a none rotated grid using nearest neighbor"
                    "interpolation"
                )
                da: xr.DataArray = da.raster.reproject(dst_crs=da.rio.crs)
            if "grid_mapping" in da.encoding:
                del da.encoding["grid_mapping"]

            rp = f"(rp {return_periods[i]})" if risk else ""
            logger.info(f"Added {hazard_type} hazard map: {da_name} {rp}")

            if not risk:
                # Set the event data arrays to the hazard grid component
                da = da.assign_attrs(
                    {
                        "name": da_name,
                        "type": hazard_type,
                        "analysis": "event",
                    }
                )
                grid.set(da)

            hazard_dataarrays.append(da)

        if risk:
            ds = xr.merge(hazard_dataarrays)
            da_names = [d.name for d in hazard_dataarrays]
            ds = ds.assign_attrs(
                {
                    "return_period": return_periods,
                    "type": hazard_type,
                    "name": da_names,
                    "analysis": "risk",
                }
            )
            self.config.set("hazard.risk", risk)
            self.config.set("hazard.return_periods", return_periods)
            grid.set(ds)

        self.config.set("hazard.file", grid._filename)
        self.config.set(
            "hazard.elevation_reference",
            "DEM" if hazard_type == "water_depth" else "datum",
        )

    def setup_vulnerability(
        self,
        vuln_fname: Path | str,
    ):
        """Set up the vulnerability from a data source.

        Parameters
        ----------
        vuln_fname : Path | str
            _description_
        """
        pass
