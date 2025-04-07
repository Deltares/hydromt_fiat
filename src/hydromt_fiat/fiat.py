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
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.region import RegionComponent

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
        self.add_component(
            "social_vulnerability_scores",
            TablesComponent(
                model=self, filename="social_vulnerability_scores/{name}.csv"
            ),
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

    @property
    def exposure_grid(self) -> GridComponent:
        """Return the exposure grid component."""
        return self.components["exposure_grid"]

    @property
    def exposure_geoms(self) -> GeomsComponent:
        """Return the exposure geoms component."""
        return self.components["exposure_geoms"]

    @property
    def social_vulnerability_data(self) -> TablesComponent:
        """Return social vulnerability tables component."""
        return self.components["social_vulnerability_scores"]

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

    @hydromt_step
    def setup_hazard(
        self,
        hazard_fnames: list[Path | str] | Path | str,
        hazard_type: str = "flooding",
        *,
        return_periods: list[int] | None = None,
        risk: bool = False,
        unit: str = "m",
    ) -> None:
        """Set up hazard maps.

        Parameters
        ----------
        hazard_fnames : list[Path | str] | Path | str
            Path(s) to the hazard file(s) or name(s) of the data catalog entries.
        hazard_type : str, optional
            Type of hazard, by default "flooding".
        return_periods : list[int] | None, optional
            List of return periods. Length of list should match the number hazard
            files, by default None.
        risk : bool, optional
            Whether the hazard files are part of a risk analysis,
            by default False.
        unit : str, optional
            The unit which the hazard data is in, by default 'm' (meters)

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

        hazard_data = {}
        for entry in hazard_fnames:
            da = self.data_catalog.get_rasterdataset(entry, geom=self.region)
            hazard_data[Path(entry).stem] = da

        # Check if there is already data set to this grid component.
        grid_like = self.hazard_grid.data if self.hazard_grid.data.sizes != {} else None

        # Parse hazard files to an xarray dataset
        ds = workflows.hazard_grid(
            grid_like=grid_like,
            hazard_data=hazard_data,
            hazard_type=hazard_type,
            return_periods=return_periods,
            risk=risk,
            unit=unit,
        )

        # Set the data to the hazard grid component
        self.hazard_grid.set(ds)

        # Set the config entries
        if len(self.hazard_grid.data.data_vars) > 1:
            self.config.set("hazard.settings.var_as_band", True)

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
        vulnerability_fname: Path | str,
        vulnerability_linking_fname: Path | str | None = None,
        *,
        unit: str = "m",
        index_name: str = "water depth",
        **select,
    ) -> None:
        """Set up the vulnerability from a data source.

        Warning
        -------
        The datasets (vulnerability_fname and vulnerability_linking_fname) \
need to have a 'type' column.

        Parameters
        ----------
        vulnerability_fname : Path | str
            Path to vulnerability dataset file or an entry in the data catalog that
            points to the vulnerability dataset file.
        vulnerability_linking_fname : Path | str | None, optional
            Path or data catalog entry of the vulnerability linking table.
            If not provided, it is assumed that the 'type' in the vulnerability dataset
            is correct, by default None
        unit : str, optional
            The unit which the vulnerability index is in, by default "m"
        index_name : str, optional
            The output name of the index column, by default "water depth"
        select : dict, optional
            Keyword arguments to select data from the 'vulnerability_fname' data source.

        Returns
        -------
            None
        """
        logger.info("Setting up the vulnerability curves")
        # Get the data from the catalog
        vulnerability_data = self.data_catalog.get_dataframe(vulnerability_fname)
        vulnerability_linking = None
        if vulnerability_linking_fname is not None:
            vulnerability_linking = self.data_catalog.get_dataframe(
                vulnerability_linking_fname
            )

        # Invoke the workflow method to create the curves from raw data
        vuln_curves, vuln_id = workflows.vulnerability_curves(
            vulnerability_data,
            vulnerability_linking=vulnerability_linking,
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

    def setup_social_vulnerability_index(self, svi_fname: str | Path):
        """Set up social vulnerability index for exposure geometries.

        Parameters
        ----------
        svi_fname : str | Path
            _description_

        Raises
        ------
        RuntimeError
            _description_
        """
        if self.exposure_geoms.data == {}:
            raise RuntimeError(
                "Exposure geometries need to be set before setting up "
                "the social vulnerability index"
            )

        svi_data = self.data_catalog.get_geodataframe(svi_fname)

        # Process SVI data
        svi_data = workflows.process_svi_data(svi_data=svi_data)

        # Set dataframe to social vulnerability index table component
        self.social_vulnerability_data.set(
            tables=svi_data.drop(columns="geometry"), name="social_vulnerability_scores"
        )

        exposure_svi_data = workflows.link_exposure_svi(
            expsure_geoms=self.exposure_geoms.data, svi_data=svi_data
        )
        self.exposure_geoms.set(exposure_svi_data, name="SVI")
