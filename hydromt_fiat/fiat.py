"""Implement fiat model class"""

from hydromt_fiat.workflows.vulnerability import Vulnerability
from hydromt_fiat.workflows.hazard import Hazard
from hydromt.models.model_grid import GridModel
from hydromt_fiat.workflows.exposure_vector import ExposureVector
import logging
from hydromt_fiat.configparser import ConfigParser
import geopandas as gpd
import pandas as pd
import hydromt
from pathlib import Path

from shapely.geometry import box
from typing import Union
from hydromt_fiat.workflows.social_vulnerability_index import SocialVulnerabilityIndex


from . import DATADIR

__all__ = ["FiatModel"]

_logger = logging.getLogger(__name__)


class FiatModel(GridModel):
    """General and basic API for the FIAT model in hydroMT."""

    _NAME = "fiat"
    _CONF = "fiat_configuration.ini"
    _GEOMS = {}  # FIXME Mapping from hydromt names to model specific names
    _MAPS = {}  # FIXME Mapping from hydromt names to model specific names
    _FOLDERS = ["hazard", "exposure", "vulnerability", "output"]
    _DATADIR = DATADIR

    def __init__(
        self,
        root=None,
        mode="w",
        config_fn=None,
        data_libs=None,
        logger=_logger,
    ):
        super().__init__(
            root=root,
            mode=mode,
            config_fn=config_fn,
            data_libs=data_libs,
            logger=logger,
        )
        self.tables = []  # List of tables to write
        self.exposure = None

    def setup_config(self, **kwargs):
        """_summary_"""
        # Setup config from HydroMT FIAT ini file
        global_settings = {}
        for k in kwargs.keys():
            global_settings[k] = kwargs[k]

        self.config["global"] = global_settings

    def setup_basemaps(
        self,
        region,
        **kwargs,
    ):
        """Define the model domain that is used to clip the raster layers.

        Adds model layer:

        * **region** geom: A geometry with the nomenclature 'region'.

        Parameters
        ----------
        region: dict
            Dictionary describing region of interest, e.g. {'bbox': [xmin, ymin, xmax, ymax]}. See :py:meth:`~hydromt.workflows.parse_region()` for all options.
        """

        kind, region = hydromt.workflows.parse_region(region, logger=self.logger)
        if kind == "bbox":
            geom = gpd.GeoDataFrame(geometry=[box(*region["bbox"])], crs=4326)
        elif kind == "grid":
            geom = region["grid"].raster.box
        elif kind == "geom":
            geom = region["geom"]
        else:
            raise ValueError(
                f"Unknown region kind {kind} for FIAT, expected one of ['bbox', 'grid', 'geom']."
            )

        # Set the model region geometry (to be accessed through the shortcut self.region).
        self.set_geoms(geom, "region")

    def setup_vulnerability(
        self,
        vulnerability_source: str,
        vulnerability_identifiers_and_linking: str,
        unit: str,
    ) -> None:
        """Setup the vulnerability curves from various possible inputs.

        Parameters
        ----------
        vulnerability_source : str
            The (relative) path or ID from the data catalog to the source of the vulnerability functions.
        vulnerability_identifiers_and_linking : str
            The (relative) path to the table that links the vulnerability functions and exposure categories.
        unit : str
            The unit of the vulnerability functions.
        """

        if not Path(vulnerability_identifiers_and_linking):
            logging.error(
                f"Vulnerability identifiers and linking table does not exist at: {vulnerability_identifiers_and_linking}"
            )

        vul = Vulnerability(self.data_catalog)
        vf_source_df = vul.get_vulnerability_source(vulnerability_source)
        self.vf_ids_and_linking_df = (
            vul.get_vulnerability_identifiers_and_linking_source(
                vulnerability_identifiers_and_linking
            )
        )
        vulnerability_output_path = "./vulnerability/vulnerability_curves.csv"
        self.tables.append(
            (
                vul.get_vulnerability_functions_from_one_file(
                    vf_source_df, self.vf_ids_and_linking_df, unit
                ),
                vulnerability_output_path,
                {"index": False, "header": False},
            )
        )

        # Store the remaining exposure and vulnerability settings.
        self.config["vulnerability"] = {"dbase_file": vulnerability_output_path}

    def setup_exposure_vector(
        self,
        asset_locations: str,
        occupancy_type: str,
        max_potential_damage: str,
        ground_floor_height: Union[int, float, str, None],
        ground_flood_height_unit: str,
    ) -> None:
        self.exposure = ExposureVector(self.data_catalog, self.region)

        if asset_locations == occupancy_type == max_potential_damage:
            # The source for the asset locations, occupancy type and maximum potential
            # damage is the same, use one source to create the exposure data.
            self.exposure.setup_from_single_source(asset_locations, ground_floor_height)

        # Link the damage functions to assets
        try:
            assert not self.vf_ids_and_linking_df.empty
        except AssertionError:
            logging.error(
                "Please call the 'setup_vulnerability' function before "
                "the 'setup_exposure_vector' function. Error message: {e}"
            )
        self.exposure.link_exposure_vulnerability(self.vf_ids_and_linking_df)
        self.exposure.check_required_columns()

        # Save the exposure data in the geoms
        exposure_output_path = "./exposure/exposure.csv"
        self.tables.append(
            (self.exposure.exposure, exposure_output_path, {"index": False})
        )

        # Store the exposure settings.
        self.config["exposure"] = {
            "dbase_file": exposure_output_path,
            "crs": self.exposure.crs,
        }

    def setup_exposure_raster(self):
        NotImplemented

    def setup_hazard(
        self,
        map_fn: str,
        map_type: str,
        rp,
        crs,
        nodata,
        var,
        chunks,
        risk_output: bool = True,
        hazard_type: str = "flooding",
    ):
        hazard = Hazard()
        hazard.setup_hazard(
            self,
            hazard_type=hazard_type,
            risk_output=risk_output,
            map_fn=map_fn,
            map_type=map_type,
            rp=rp,
            crs=crs,
            nodata=nodata,
            var=var,
            chunks=chunks,
            region=self.region,
        )

        # Store the hazard settings.
        hazard_settings = {}
        hazard_maps = []
        for hazard_map in self.maps.keys():
            hazard_maps.append(
                str(Path("hazard") / (self.maps[hazard_map].name + ".nc"))
            )

        hazard_settings["grid_file"] = hazard_maps

        if not isinstance(rp, list):
            rp = "Event"
        hazard_settings["return_period"] = rp

        hazard_settings["crs"] = hazard.crs
        hazard_settings["spatial_reference"] = map_type
        self.config["hazard"] = hazard_settings

    def setup_social_vulnerability_index(
        self, census_key: str, path: str, state_abbreviation: str
    ):

        # Create SVI object
        svi = SocialVulnerabilityIndex(self.data_catalog, self.config)

        # Call functionalities of SVI
        svi.set_up_census_key(census_key)
        svi.variable_code_csv_to_pd_df(path)
        svi.set_up_download_codes()
        svi.set_up_state_code(state_abbreviation)
        svi.download_census_data()
        svi.rename_census_data("Census_code_withE", "Census_variable_name")
        svi.create_indicator_groups("Census_variable_name", "Indicator_code")
        svi.processing_svi_data()
        svi.normalization_svi_data()
        svi.domain_scores()
        svi.composite_scores()

    # TO DO: JOIN WITH GEOMETRIES. FOR MAPPING.
    # this link can be used: https://github.com/datamade/census

    def read(self):
        """Method to read the complete model schematization and configuration from file."""
        self.logger.info(f"Reading model data from {self.root}")
        self.read_config(config_fn=str(Path(self.root).joinpath("settings.toml")))

        # TODO: determine if it is required to read the hazard files
        # hazard_maps = self.config["hazard"]["grid_file"]
        # self.read_grid(fn="hazard/{name}.nc")

        # Read the exposure data
        self.read_exposure(Path(self.root).joinpath("exposure", "exposure.csv"))

        # Read the vulnerability data
        self.read_vulnerability()

    def _configread(self, fn):
        """Parse fiat configuration toml file to dict."""
        # TODO: update to FIAT toml file

        # Read the fiat configuration toml file.
        parser = ConfigParser()
        return parser.load_file(fn)

    def read_exposure(self, fn):
        """_summary_"""

        path = Path(fn)
        self.logger.debug(f"Reading file {str(path)}")
        _fn = Path(self.root) / path
        if not _fn.is_file():
            logging.warning(f"File {_fn} does not exist!")

        if path.name.endswith("csv"):
            self.exposure = ExposureVector()
            self.exposure.read(_fn)

    def read_vulnerability(self, fn):
        NotImplemented

    def write(self):
        """Method to write the complete model schematization and configuration to file."""

        self.logger.info(f"Writing model data to {self.root}")
        if self.config:  # try to read default if not yet set
            self.write_config()
        if self.maps:
            self.write_maps(fn="hazard/{name}.nc")
        if self.geoms:
            self.write_geoms(fn="exposure/{name}.geojson")
        if self.tables:
            self.write_tables()

    def write_tables(self) -> None:
        if len(self.tables) == 0:
            self.logger.debug("No table data found, skip writing.")
            return
        self._assert_write_mode
        for (data, path, kwargs) in self.tables:
            path = Path(path)
            if not isinstance(data, (pd.DataFrame)) or len(data.index) == 0:
                self.logger.warning(
                    f"{path.name} object of type {type(data).__name__} not recognized"
                )
                continue
            self.logger.debug(f"Writing file {str(path)}")
            _fn = Path(self.root) / path
            if not _fn.parent.is_dir():
                _fn.parent.mkdir(parents=True)

            if path.name.endswith("csv"):
                data.to_csv(_fn, **kwargs)
            elif path.name.endswith("xlsx"):
                data.to_excel(_fn, **kwargs)

    def _configwrite(self, fn):
        """Write config to Delft-FIAT configuration toml file."""
        # Save the configuration file.
        ConfigParser().save(self.config, Path(self.root).joinpath("settings.toml"))
