"""Main module."""

import logging
from pathlib import Path

import geopandas as gpd
from hydromt.model import Model
from hydromt.model.components import (
    ConfigComponent,
    GeomsComponent,
    GridComponent,
    TablesComponent,
)
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.components import (
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
        mode: str = "r",
        data_libs: list[str] | str | None = None,
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
        self.add_component(
            "exposure_data",
            TablesComponent(model=self),
        )
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
    def hazard_grid(self) -> HazardGridComponent:
        """Return hazard grid component."""
        return self.components["hazard_grid"]

    @property
    def vulnerability_data(self) -> VulnerabilityComponent:
        """Return the vulnerability component containing the data."""
        return self.components["vulnerability_data"]

    @property
    def exposure_grid(self) -> GridComponent:
        """Return the exposure grid component."""
        return self.components["exposure_grid"]

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
    def setup_exposure_grid(
        self,
        exposure_grid_fnames: str | Path | list[str | Path],
        exposure_grid_link_fname: str | Path,
    ) -> None:
        """Set up an exposure grid.

        Parameters
        ----------
        exposure_grid_fnames : str | Path | list[str  |  Path]
            Name of or path to exposure file(s)
        exposure_grid_link_fname : str | Path
            Table containing the names of the exposure files and corresponding
            vulnerability curves.
        """
        logger.info("Setting up exposure grid")

        if self.vulnerability_data.data == {}:
            raise RuntimeError(
                "setup_vulnerability step is required before setting up exposure grid."
            )
        if self.region is None:
            raise MissingRegionError("Region is required for setting up exposure grid.")

        # Check if linking_table exists
        if not Path(exposure_grid_link_fname).exists():
            raise ValueError("Given path to linking table does not exist.")
        # Read linking table
        exposure_linking = self.data_catalog.get_dataframe(exposure_grid_link_fname)

        # Check if linking table columns are named according to convention
        for col_name in ["type", "curve_id"]:
            if col_name not in exposure_linking.columns:
                raise ValueError(
                    f"Missing column, '{col_name}' in exposure grid linking table"
                )

        exposure_files = (
            [exposure_grid_fnames]
            if not isinstance(exposure_grid_fnames, list)
            else exposure_grid_fnames
        )

        # Read exposure data files from data catalog
        exposure_data = {}
        for exposure_file in exposure_files:
            exposure_fn = Path(exposure_file).stem
            da = self.data_catalog.get_rasterdataset(exposure_file, geom=self.region)
            exposure_data[exposure_fn] = da

        # Get grid like from existing exposure data if there is any
        grid_like = self.exposure_grid.data if self.exposure_grid.data != {} else None

        # Execute the workflow function
        ds = workflows.exposure_grid_data(
            grid_like=grid_like,
            exposure_data=exposure_data,
            exposure_linking=exposure_linking,
        )

        # Set the dataset
        self.exposure_grid.set(ds)

        # Set the config entries
        if len(self.exposure_grid.data.data_vars) > 1:
            self.config.set("exposure.grid.settings.var_as_band", True)
        self.config.set("exposure.grid.file", self.exposure_grid._filename)
