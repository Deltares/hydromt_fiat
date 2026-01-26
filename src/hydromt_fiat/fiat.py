"""Main module."""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
from hydromt.model import Model
from hydromt.model.components import SpatialModelComponent
from hydromt.model.steps import hydromt_step
from pyproj.crs import CRS

from hydromt_fiat.components import (
    ConfigComponent,
    ExposureGeomsComponent,
    ExposureGridComponent,
    HazardComponent,
    RegionComponent,
    VulnerabilityComponent,
)
from hydromt_fiat.utils import (
    CONFIG,
    EXPOSURE,
    GEOM,
    GRID,
    HAZARD,
    REGION,
    SETTINGS,
    VULNERABILITY,
)

# Set some global variables
__all__ = ["FIATModel"]
__hydromt_eps__ = ["FIATModel"]  # core entrypoints

# Create a logger
logger = logging.getLogger(f"hydromt.{__name__}")


class FIATModel(Model):
    """Read or write a FIAT model.

    Parameters
    ----------
    root : str, optional
        Model root, by default None.
    config_fname : str, optional
        Name of the configurations file, by default 'settings.toml'.
    mode : {'r','r+','w'}, optional
        read/append/write mode, by default "w".
    data_libs : list[str] | str, optional
        List of data catalog configuration files, by default None.
    **catalog_keys : dict
        Additional keyword arguments to be passed down to the DataCatalog.
    """

    name: str = "fiat"
    # supported model version should be filled by the plugins
    # e.g. _MODEL_VERSION = ">=1.0, <1.1"
    _MODEL_VERSION = None

    def __init__(
        self,
        root: str | None = None,
        config_fname: str = f"{SETTINGS}.toml",
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
            CONFIG,
            ConfigComponent(model=self, filename=config_fname),
        )
        self.add_component(
            f"{EXPOSURE}_{GEOM}",
            ExposureGeomsComponent(model=self, region_component=REGION),
        )
        self.add_component(
            f"{EXPOSURE}_{GRID}",
            ExposureGridComponent(model=self, region_component=REGION),
        )
        self.add_component(
            HAZARD,
            HazardComponent(model=self, region_component=REGION),
        )
        self.add_component(
            VULNERABILITY,
            VulnerabilityComponent(model=self),
        )

    ## Properties
    @property
    def config(self) -> ConfigComponent:
        """Access the config component."""
        return self.components[CONFIG]

    @property
    def exposure_geoms(self) -> ExposureGeomsComponent:
        """Access the exposure geoms component."""
        return self.components[f"{EXPOSURE}_{GEOM}"]

    @property
    def exposure_grid(self) -> ExposureGridComponent:
        """Access the exposure grid component."""
        return self.components[f"{EXPOSURE}_{GRID}"]

    @property
    def hazard(self) -> HazardComponent:
        """Access the hazard component."""
        return self.components[HAZARD]

    @property
    def region(self) -> gpd.GeoDataFrame:
        """Return the model's region.

        This will return a polygon covering the current region of the model.
        """
        return self.components[REGION].region

    @property
    def vulnerability(self) -> VulnerabilityComponent:
        """Access the vulnerability component."""
        return self.components[VULNERABILITY]

    ## I/O
    @hydromt_step
    def read(self) -> None:
        """Read the FIAT model."""
        super().read()

    @hydromt_step
    def write(self) -> None:
        """Write the FIAT model."""
        names = list(self.components.keys())
        names.remove(CONFIG)
        for name in names:
            self.components[name].write()
        self.config.write()

    ## Mutating methods
    @hydromt_step
    def clear(self):
        """Clear the model.

        All data from the components are deleted.
        The region is deleted.
        """
        for component in self.components.values():
            component.clear()

    @hydromt_step
    def clip(
        self,
        region: Path | str | gpd.GeoDataFrame,
    ) -> None:
        """Clip the model based on a new (smaller) region.

        All grid-based components are clipped with a buffer of 1 cell.

        Parameters
        ----------
        region : Path | str | gpd.GeoDataFrame
            The region to be used for clipping. It can either be a path to a vector
            file or a geopandas GeoDataFrame.
        """
        # First update the region to the new region, thereby replace
        self.setup_region(region, replace=True)
        logger.info(
            f"Clipping FIAT model with geometry with bbox {self.region.total_bounds}"
        )
        # Call the clip methods of the spatial components
        for name, component in self.components.items():
            if not isinstance(component, SpatialModelComponent) or name == REGION:
                continue
            component.clip(self.region, inplace=True)

    @hydromt_step
    def reproject(
        self,
        crs: CRS | int | str | None = None,
    ) -> None:
        """Reproject the model to a specific coordinate system.

        Parameters
        ----------
        crs : CRS | int | str | None, optional
            The coordinate system to reproject to. If None, the model crs is used, which
            is derived from the region, for reprojecting all spatial components.
            By default None.
        """
        crs = crs or self.crs
        if crs is None:
            raise ValueError(
                "crs was not provided nor found in the model 'crs' attribute"
            )
        # Call the reproject methods of the spatial components
        for _, component in self.components.items():
            if not isinstance(component, SpatialModelComponent):
                continue
            component.reproject(crs, inplace=True)

    ## Setup methods
    @hydromt_step
    def setup_config(
        self,
        **settings: dict[str, Any],
    ) -> None:
        """Set config file entries.

        Parameters
        ----------
        settings : dict
            Settings for the configuration provided as keyword arguments
            (KEY=VALUE).
        """
        logger.info("Setting config entries from user input")
        for key, value in settings.items():
            self.config.set(key, value)

    @hydromt_step
    def setup_region(
        self,
        region: Path | str | gpd.GeoDataFrame,
        replace: bool = False,
    ) -> None:
        """Set the region of the FIAT model.

        Parameters
        ----------
        region : Path | str | gpd.GeoDataFrame
            Path to the region vector file or a loaded vector file that takes the form
            of a geopandas GeoDataFrame.
        replace : bool, optional
            If False, a union is created between given and existing geometries.
            By default False.
        """
        if isinstance(region, (Path, str)):
            region = Path(region)
            logger.info(f"Setting region from '{region.as_posix()}'")
            if not region.is_file():
                raise FileNotFoundError(region.as_posix())
            geom = gpd.read_file(region)
        elif isinstance(region, gpd.GeoDataFrame):
            geom = region
        else:
            raise TypeError(
                "Region should either be of type \
`gpd.GeoDataframe` or `Path`/ `str`"
            )
        # Set the region in the region component
        self.components[REGION].set(geom, replace=replace)
