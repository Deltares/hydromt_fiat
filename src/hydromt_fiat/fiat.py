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

import hydromt_fiat.workflows as workflows
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
            components={
                "region": RegionComponent(model=self, filename="region/{name}.geojson")
            },
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
            GeomsComponent(
                model=self,
                region_component="region",
                filename="exposure/{name}.fgb",
            ),
        )
        self.add_component(
            "exposure_grid",
            GridComponent(model=self, region_component="region"),
        )
        self.add_component(
            "hazard_grid",
            GridComponent(model=self, region_component="region"),
        )
        self.add_component(
            "vulnerability_data",
            TablesComponent(model=self, filename="vulnerability/{name}.csv"),
        )

    ## Properties
    @property
    def config(self) -> ConfigComponent:
        """Return the configurations component."""
        return self.components["config"]

    @property
    def vulnerability_data(self) -> TablesComponent:
        """Return the vulnerability component containing the data."""
        return self.components["vulnerability_data"]

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
        hazard_fname: Path,
    ):
        """Set up hazard from a data source.

        Parameters
        ----------
        hazard_fname : Path
            _description_
        """
        pass

    @hydromt_step
    def setup_vulnerability(
        self,
        vuln_fname: Path | str,
        vuln_link_fname: Path | str | None = None,
        unit: str = "m",
        index_name: str = "water depth",
        **select,
    ):
        """Set up the vulnerability from a data source.

        Parameters
        ----------
        vuln_fname : Path | str
            _description_
        vuln_link_fname : Path | str | None, optional
            _description_, by default None
        unit : str, optional
            _description_, by default "m"
        index_name : str, optional
            _description_, by default "water depth"
        select : dict, optional
            Keyword arguments to select data from the 'vuln_fname' data source.
        """
        # Get the data from the catalog
        vuln_data = self.data_catalog.get_dataframe(vuln_fname)
        vuln_linking = None
        if vuln_link_fname is not None:
            vuln_linking = self.data_catalog.get_dataframe(vuln_link_fname)

        # Invoke the workflow method to create the curves from raw data
        vuln_curves, vuln_id = workflows.vulnerability_curves(
            vuln_data,
            vuln_linking=vuln_linking,
            unit=unit,
            index_name=index_name,
            **select,
        )

        self.vulnerability_data.set(vuln_curves, "vulnerability_curves")
        self.vulnerability_data.set(vuln_id, "vulnerability_identifiers")

        self.config.set(
            "vulnerability.file",
            self.vulnerability_data._filename.format(name="vulnerability_curves"),
        )
