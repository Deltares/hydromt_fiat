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
from hydromt_fiat.components import RegionComponent
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
            GridComponent(
                model=self, region_component="region", filename="hazard/hazard_grid.nc"
            ),
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
    def hazard_grid(self) -> GridComponent:
        """Return hazard grid component."""
        return self.components["hazard_grid"]

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
        exposure_link_fname: Path | str | None,
    ):
        """Set up the exposure from a data source.

        Parameters
        ----------
        exposure_fname : Path | str
            _description_
        """
        # Check for region
        if self.region is None:
            # TODO Replace with custom error class
            raise AttributeError(
                "Region is None -> \
use 'setup_region' before this method"
            )
        # Check for vulnerability
        keys = ["vulnerability_curves", "vulnerability_identifiers"]
        if not all([item in self.vulnerability_data.data for item in keys]):
            # TODO Replace with custom error class
            raise KeyError("Use setup_vulnerability before this method")

        # Get ze data
        exposure_data = self.data_catalog.get_geodataframe(
            data_like=exposure_fname,
            geom=self.region,
        )
        exposure_link_data = None
        if exposure_link_fname is not None:
            exposure_link_data = self.data_catalog.get_dataframe(
                data_like=exposure_link_fname,
            )

        # Call the workflows method to manipulate the data
        exposure_vector, exposure_table = workflows.exposure_geometries(
            exposure_data=exposure_data,
            exposure_type_column=exposure_type_column,
            vulnerability=self.vulnerability_data.data["vulnerability_identifiers"],
            exposure_link_data=exposure_link_data,
        )

        # Set the config file
        pass

    @hydromt_step
    def setup_exposure_grid(
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
        hazard_fnames: list[Path | str] | Path | str,
        return_periods: list[int] | None = None,
        hazard_type: str | None = "flooding",
        *,
        risk: bool = False,
    ) -> None:
        """Set up hazard maps.

        Parameters
        ----------
        hazard_fnames : list[Path | str] | Path | str
            Path(s) to the hazard file(s) or name(s) of the data catalog entries.
        return_periods : list[int] | None, optional
            List of return periods. Length of list should match the number hazard
            files, by default None.
        hazard_type : str | None, optional
            Type of hazard, by default "flooding".
        risk : bool, optional
            Whether the hazard files are part of a risk analysis,
            by default False.

        Returns
        -------
            None
        """
        logger.info("Setting up hazard raster data")
        if not isinstance(hazard_fnames, list):
            hazard_fnames = [hazard_fnames]
        if risk and not return_periods:
            raise ValueError("Cannot perform risk analysis without return periods")
        if risk and len(return_periods) != len(hazard_fnames):
            raise ValueError("Return periods do not match the number of hazard files")

        if self.region is None:
            raise MissingRegionError(
                "Region component is missing for setting up hazard data."
            )

        # Check if there is already data set to this grid component.
        grid_like = self.hazard_grid.data if self.hazard_grid.data.sizes != {} else None

        # Parse hazard files to an xarray dataset
        ds = workflows.hazard_data(
            grid_like=grid_like,
            region=self.region,
            data_catalog=self.data_catalog,
            hazard_fnames=hazard_fnames,
            hazard_type=hazard_type,
            return_periods=return_periods,
            risk=risk,
        )

        # Set the data to the hazard grid component
        self.hazard_grid.set(ds)

        if risk:
            self.config.set("hazard.risk", risk)
            self.config.set("hazard.return_periods", return_periods)

        self.config.set("hazard.file", self.hazard_grid._filename)
        self.config.set(
            "hazard.elevation_reference",
            "DEM" if hazard_type == "water_depth" else "datum",
        )

    @hydromt_step
    def setup_vulnerability(
        self,
        vuln_fname: Path | str,
        vuln_link_fname: Path | str | None = None,
        *,
        unit: str = "m",
        index_name: str = "water depth",
        **select,
    ) -> None:
        """Set up the vulnerability from a data source.

        Warning
        -------
        The datasets (vuln_fname and vuln_link_fname) need to have a 'type' column.

        Parameters
        ----------
        vuln_fname : Path | str
            Path to vulnerability dataset file or an entry in the data catalog that
            points to the vulnerability dataset file.
        vuln_link_fname : Path | str | None, optional
            Path or data catalog entry of the vulnerability linking table.
            If not provided, it is assumed that the 'type' in the vulnerability dataset
            is correct, by default None
        unit : str, optional
            The unit which the vulnerability index is in, by default "m"
        index_name : str, optional
            The output name of the index column, by default "water depth"
        select : dict, optional
            Keyword arguments to select data from the 'vuln_fname' data source.

        Returns
        -------
            None
        """
        logger.info("Setting up the vulnerability curves")
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
