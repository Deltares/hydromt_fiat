"""Main module."""

import logging
from pathlib import Path

import geopandas as gpd
from hydromt.model import Model
from hydromt.model.components import (
    ConfigComponent,
    GeomsComponent,
    TablesComponent,
)
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.components import (
    ExposureGridComponent,
    HazardGridComponent,
    RegionComponent,
    VulnerabilityComponent,
)
from hydromt_fiat.errors import MissingRegionError

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
            components={"region": RegionComponent(model=self)},
            mode=mode,
            region_component="region",
            data_libs=data_libs,
            **catalog_keys,
        )

        ## Setup components
        self.add_component(
            "config",
            ConfigComponent(model=self, filename=config_fname),
        )
        self.add_component(
            "exposure_data",
            TablesComponent(model=self),
        )
        self.add_component(
            "exposure_geoms",
            GeomsComponent(model=self, region_component="region"),
        )
        self.add_component(
            "exposure_grid",
            ExposureGridComponent(model=self, region_component="region"),
        )
        self.add_component(
            "hazard_grid",
            HazardGridComponent(model=self, region_component="region"),
        )
        self.add_component(
            "vulnerability_data",
            VulnerabilityComponent(model=self),
        )

    ## Properties
    @property
    def config(self) -> ConfigComponent:
        """Return the configurations component."""
        return self.components["config"]

    @property
    def exposure_geoms(self) -> GeomsComponent:
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
        Model.write(self)

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
        self.components["region"].set(geom)

    @hydromt_step
    def setup_exposure_geoms(
        self,
        exposure_fname: Path | str,
        exposure_type_column: str,
        *,
        exposure_link_fname: Path | str | None,
    ) -> None:
        """Set up the exposure from a data source.

        Parameters
        ----------
        exposure_fname : Path | str
            _description_
        exposure_type_column : str
            _description_
        exposure_link_fname : Path | str | None
            _description_
        """
        logger.info("Setting up exposure geometries")
        # Check for region
        if self.region is None:
            # TODO Replace with custom error class
            raise MissingRegionError(
                "Region is None -> \
use 'setup_region' before this method"
            )
        # Check for vulnerability
        keys = ["vulnerability_curves", "vulnerability_identifiers"]
        if not all([item in self.vulnerability_data.data for item in keys]):
            # TODO Replace with custom error class
            raise RuntimeError("Use setup_vulnerability before this method")

        # Guarantee typing
        exposure_fname = Path(exposure_fname)

        # Get ze data
        exposure_data = self.data_catalog.get_geodataframe(
            data_like=exposure_fname,
            geom=self.region,
        )
        exposure_linking = None
        if exposure_link_fname is not None:
            exposure_linking = self.data_catalog.get_dataframe(
                data_like=exposure_link_fname,
            )

        # Call the workflows function(s) to manipulate the data
        exposure_vector = workflows.exposure_geom_linking(
            exposure_data=exposure_data,
            exposure_type_column=exposure_type_column,
            vulnerability=self.vulnerability_data.data["vulnerability_identifiers"],
            exposure_linking=exposure_linking,
        )

        # Set the data in the component
        self.exposure_geoms.set(exposure_vector, name=exposure_fname.stem)

        # Set the config file
        n = len(self.exposure_geoms.data)
        self.config.set(f"exposure.geom.file{n}", f"exposure/{exposure_fname.stem}.fgb")

    @hydromt_step
    def setup_exposure_max_damage(
        self,
        exposure_name: str,
        exposure_type: str,
        exposure_cost_table_fname: Path | str | None = None,
        **select: dict,
    ) -> None:
        """_summary_.

        Parameters
        ----------
        exposure_type : str
            _description_
        exposure_cost_table : Path | str, optional
            _description_

        Returns
        -------
        None
        """
        logger.info(f"Setting up maximum potential damage for {exposure_name}")
        # Some checks on the input
        if exposure_name not in self.exposure_geoms.data:
            raise RuntimeError(
                f"Run `setup_exposure_geoms` before this methods \
with '{exposure_name}' as input or chose from already present geometries: \
{list(self.exposure_geoms.data.keys())}"
            )
        exposure_cost_table = None
        if exposure_cost_table_fname is not None:
            exposure_cost_table = self.data_catalog.get_dataframe(
                exposure_cost_table_fname,
            )

        # Call the workflows function to add the max damage
        exposure_vector = workflows.max_monetary_damage(
            self.exposure_geoms.data[exposure_name],
            exposure_cost_table=exposure_cost_table,
            exposure_type=exposure_type,
            vulnerability=self.vulnerability_data.data["vulnerability_identifiers"],
            **select,
        )

        # Set the data back, its a bit symbolic as the dataframe is mutable...
        self.exposure_geoms.set(exposure_vector, exposure_name)
