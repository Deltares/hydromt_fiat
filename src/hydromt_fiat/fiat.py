"""Main module."""

import logging
from pathlib import Path

import geopandas as gpd
from hydromt.model import Model
from hydromt.model.steps import hydromt_step

from hydromt_fiat.components import (
    ExposureGeomsComponent,
    ExposureGridComponent,
    FIATConfigComponent,
    HazardGridComponent,
    RegionComponent,
    VulnerabilityComponent,
)
from hydromt_fiat.utils import REGION

# Set some global variables
__all__ = ["FIATModel"]
__hydromt_eps__ = ["FIATModel"]  # core entrypoints

# Create a logger
logger = logging.getLogger(f"hydromt.{__name__}")


class FIATModel(Model):
    """Read or Write a FIAT model.

    Parameters
    ----------
    root : str, optional
        Model root, by default None
    config_fname : str, optional
        Name of the configurations file, by default 'settings.toml'
    mode : {'r','r+','w'}, optional
        read/append/write mode, by default "w"
    data_libs : list[str] | str, optional
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
        config_fname: str = "settings.toml",
        *,
        mode: str = "r",
        data_libs: list[str] | str | None = None,
        **catalog_keys,
    ):
        super().__init__(
            root,
            components={REGION: RegionComponent(model=self)},
            mode=mode,
            region_component=REGION,
            data_libs=data_libs,
            **catalog_keys,
        )

        ## Setup components
        self.add_component(
            "config",
            FIATConfigComponent(model=self, filename=config_fname),
        )
        self.add_component(
            "exposure_geoms",
            ExposureGeomsComponent(model=self, region_component=REGION),
        )
        self.add_component(
            "exposure_grid",
            ExposureGridComponent(model=self, region_component=REGION),
        )
        self.add_component(
            "hazard_grid",
            HazardGridComponent(model=self, region_component=REGION),
        )
        self.add_component(
            "vulnerability_data",
            VulnerabilityComponent(model=self),
        )

    ## Properties
    @property
    def config(self) -> FIATConfigComponent:
        """Return the configurations component."""
        return self.components["config"]

    @property
    def exposure_geoms(self) -> ExposureGeomsComponent:
        """Return the exposure geoms component."""
        return self.components["exposure_geoms"]

    @property
    def exposure_grid(self) -> ExposureGridComponent:
        """Return the exposure grid component."""
        return self.components["exposure_grid"]

    @property
    def hazard_grid(self) -> HazardGridComponent:
        """Return hazard grid component."""
        return self.components["hazard_grid"]

    @property
    def region_data(self) -> RegionComponent:
        """Return the region component."""
        return self.components[REGION]

    @property
    def vulnerability_data(self) -> VulnerabilityComponent:
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
        components = list(self.components.keys())
        cfg = None
        for c in [self.components[name] for name in components]:
            if isinstance(c, FIATConfigComponent):
                cfg = c
                continue
            c.write()
        if cfg is not None:
            cfg.write()

    ## Setup methods
    @hydromt_step
    def setup_config(
        self,
        **settings: dict,
    ) -> None:
        """Set config file entries.

        Parameters
        ----------
        settings : dict
            Settings for the configuration provided as keyword arguments
            (KEY=VALUE).

        Returns
        -------
            None
        """
        logger.info("Setting config entries from user input")
        for key, value in settings.items():
            self.config.set(key, value)

    @hydromt_step
    def setup_region(
        self,
        region: Path | str,
    ) -> None:
        """Set the region of the FIAT model.

        Parameters
        ----------
        region : Path | str
            Path to the region vector file.

        Returns
        -------
            None
        """
        region = Path(region)
        logger.info(f"Setting region from '{region.as_posix()}'")
        if not region.is_file():
            raise FileNotFoundError(region.as_posix())
        geom = gpd.read_file(region)
        self.components[REGION].set(geom)
