"""Main module."""

import logging
from pathlib import Path
from typing import List, Union

import geopandas as gpd
from hydromt.model import Model
from hydromt.model.components import (
    ConfigComponent,
    GeomsComponent,
    GridComponent,
    TablesComponent,
)
from hydromt.model.steps import hydromt_step

from hydromt_fiat.components import RegionComponent
from hydromt_fiat.workflows import parse_hazard_data

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

    @property
    def hazard_grid(self):
        """Return hazard grid component."""
        return self.components["hazard_grid"]

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
        hazard_fnames: str | list[str],
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

        # Check if there is already data set to this grid component. This will cause
        # problems with setting attrs
        if not self.hazard_grid.data.sizes == {}:
            raise ValueError("Cannot set hazard data on existing hazard grid data.")

        # Parse hazard files to an xarray dataset
        ds = parse_hazard_data(
            data_catalog=self.data_catalog,
            hazard_fnames=hazard_fnames,
            hazard_type=hazard_type,
            return_periods=return_periods,
            risk=risk,
        )

        self.hazard_grid.set(ds)

        if risk:
            self.config.set("hazard.risk", risk)
            self.config.set("hazard.return_periods", return_periods)

        self.config.set("hazard.file", self.hazard_grid._filename)
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
