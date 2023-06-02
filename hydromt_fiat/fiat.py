"""Implement fiat model class"""

from hydromt.models.model_grid import GridModel
import logging
import geopandas as gpd
import pandas as pd
import xarray as xr
import hydromt
from pathlib import Path
from os.path import join, basename, isfile, basename
import glob

from shapely.geometry import box
from typing import Union

from .config import Config
from .workflows.vulnerability import Vulnerability
from .workflows import hazard
from .workflows.exposure_vector import ExposureVector
from .workflows.social_vulnerability_index import SocialVulnerabilityIndex

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
    _CLI_ARGS = {"region": "setup_basemaps"}
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
        self.tables = dict()  # Dictionnary of tables to write
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
        vulnerability_fn: Union[str, Path],
        vulnerability_identifiers_and_linking_fn: Union[str, Path],
        unit: str,
    ) -> None:
        """Setup the vulnerability curves from various possible inputs.

        Parameters
        ----------
        vulnerability_fn : str
            The (relative) path or ID from the data catalog to the source of the vulnerability functions.
        vulnerability_identifiers_and_linking_fn : str
            The (relative) path to the table that links the vulnerability functions and exposure categories.
        unit : str
            The unit of the vulnerability functions.
        """

        if not Path(vulnerability_identifiers_and_linking_fn):
            logging.error(
                f"Vulnerability identifiers and linking table does not exist at: {vulnerability_identifiers_and_linking_fn}"
            )

        # Read the vulnerability table and instantiate the Vulnerability class
        df_vulnerability = self.data_catalog.get_dataframe(vulnerability_fn)
        vulnerability = Vulnerability(unit)

        # Read the vulnerability identifiers and linking table
        vf_ids_and_linking_df = self.data_catalog.get_dataframe(vulnerability_identifiers_and_linking_fn)
        # Link the vulnerability functions to the indentifiers
        vulnerability.get_vulnerability_functions_from_one_file(
            df_source = df_vulnerability, 
            df_identifiers_linking = vf_ids_and_linking_df,
        )
        # Add to tables property
        self.set_tables(df = vulnerability.get_table(), name = "vulnerability")
        # Also add the identifiers
        self.set_tables(df = vf_ids_and_linking_df, name = "vulnerability_identifiers")

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

        # add to tables
        self.set_tables(df = self.exposure.exposure_db, name = "exposure")
        # Update config
        self.set_config("exposure.type", "vector")
        self.set_config("exposure.crs", self.exposure.crs)

    def setup_exposure_raster(self):
        NotImplemented

    def setup_hazard(
        self,
        map_fn: str,
        map_type: str,
        rp,
        var,
        risk_output: bool = True,
        hazard_type: str = "flooding",
    ):
        """
        Prepare hazard map.

        To set the crs, chunks, nodata please use data catalog.
        """

        map_fn_lst, map_type_lst, rp_lst, var_lst = hazard.checkInputs(
            root = self.root,
            hazard_type=hazard_type,
            risk_output=risk_output,
            map_fn=map_fn,
            map_type=map_type,
            rp=rp,
            var=var,
        )

        # Read the data here
        da_lst = []
        list_names = []
        for idx, da_map_fn in enumerate(map_fn_lst):
            da = self.data_catalog.get_rasterdataset(
                da_map_fn, 
                bbox=self.region.total_bounds,
                single_var_as_array=True,
            )
            da, da_dict = hazard.processMap(
                da=da,
                ds_like = self.grid,
                da_name=da_map_fn,
                map_type=map_type_lst[idx],
                var=var_lst[idx],
                rp=rp_lst[idx],
                risk_output=risk_output,
            )
            da_name = da_dict.keys()[0]
            list_names.append(da_name)
            # Add da_dict to model config
            self.set_config("hazard", da_dict)
            # Append to da_lst
            da_lst.append(da)
            # Add da to maps
            self.set_maps(da, da_name)
        
        # # Check, in ReadMaps there seemed to be some concat but di not end up anywhere?
        # # Looking at the merging should var only be a single str and not a list?
        # da_all = xr.concat(da_lst, dim="rp")
        # if not risk_output:
        #     ds = da_all.to_dataset(name="EVENT")
        #     ds.attrs.update({
        #         "returnperiod": rp_lst, 
        #         "type": map_type_lst,
        #         "name": list_names,
        #         "Analysis": "Event base"
        #     })
        # else:
        #     ds = da_all.to_dataset(name="RISK")
        #     ds.attrs.update({
        #         "returnperiod": rp_lst, 
        #         "type": map_type_lst,
        #         "name": list_names,
        #         "Analysis": "Risk"
        #     })
        
        # # Add ds to maps??
        # self.set_maps(ds, "hazard")

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
        self, census_key: str, path: str, state_abbreviation: str, path_dataset: str
    ):
        # Create SVI object
        svi = SocialVulnerabilityIndex(self.data_catalog, self.config)

        # Call functionalities of SVI
        svi.set_up_census_key(census_key)
        #svi.read_dataset(path_dataset)
        svi.variable_code_csv_to_pd_df(path)
        svi.set_up_download_codes()
        svi.set_up_state_code(state_abbreviation)
        svi.download_census_data()
        svi.rename_census_data("Census_code_withE", "Census_variable_name")
        svi.identify_no_data()
        svi.check_nan_variable_columns()
        svi.print_missing_variables("Census_variable_name", "Indicator_code")
        translation_variable_to_indicator = svi.create_indicator_groups("Census_variable_name", "Indicator_code")
        svi.processing_svi_data(translation_variable_to_indicator)
        svi.normalization_svi_data()
        svi.domain_scores()
        svi.composite_scores()
        print("hi")

    # TO DO: JOIN WITH GEOMETRIES. FOR MAPPING.
    # this link can be used: https://github.com/datamade/census

    # I/O
    def read(self):
        """Method to read the complete model schematization and configuration from file."""
        self.logger.info(f"Reading model data from {self.root}")

        # Read the configuration file
        self.read_config(config_fn=str(Path(self.root).joinpath("settings.toml")))

        # TODO: determine if it is required to read the hazard files
        # hazard_maps = self.config["hazard"]["grid_file"]
        # self.read_grid(fn="hazard/{name}.nc")

        # Read the tables exposure and vulnerability
        self.read_tables()

    def _configread(self, fn):
        """Parse fiat configuration toml file to dict."""
        # TODO: update to FIAT toml file

        # Read the fiat configuration toml file.
        config = Config()
        return config.load_file(fn)

    def check_path_exists(self, fn):
        """TODO: decide to use this or another function (check_file_exist in validation.py)"""
        path = Path(fn)
        self.logger.debug(f"Reading file {str(path.name)}")
        if not fn.is_file():
            logging.warning(f"File {fn} does not exist!")

    def read_tables(self):
        """Read the model tables for vulnerability and exposure data."""
        if not self._write:
            self._tables = dict()  # start fresh in read-only mode

        self.logger.info("Reading model table files.")
        
        # Start with vulnerability table
        vulnerability_fn = self.get_config(
            "vulnerability.dbase_file", 
            "vulnerability/vulnerability_curves.csv"
        )
        if Path(vulnerability_fn).is_file:
            self.logger.debug(f"Reading vulnerability table {vulnerability_fn}")
            vf = Vulnerability()
            df = vf.read(vulnerability_fn)
            self._tables["vulnerability"] = df
        else:
            logging.warning(f"File {vulnerability_fn} does not exist!")
        
        # Now with exposure
        exposure_fn = self.get_config(
            "exposure.dbase_file", 
            "exposure/exposure.csv"
        )
        if Path(exposure_fn).is_file:
            self.logger.debug(f"Reading exposure table {exposure_fn}")
            ef = ExposureVector(crs = self.get_config("exposure.crs", self.crs))
            df = ef.read(exposure_fn)
            self._tables["exposure"] = df
        else:
            logging.warning(f"File {exposure_fn} does not exist!")
        
        # If needed read other tables files like vulnerability identifiers
        # Comment if not needed - I usually use os rather than pathlib, change if you prefer
        fns = glob.glob(join(self.root, f"*.csv"))
        if len(fns) > 0:
            for fn in fns:
                self.logger.info(f"Reading table {fn}")
                name = basename(fn).split(".")[0]
                tbl = pd.read_csv(fn)
                self.set_tables(tbl, name=name)

    def write(self):
        """Method to write the complete model schematization and configuration to file."""
        self.logger.info(f"Writing model data to {self.root}")

        if self.exposure:
            exposure_output_path = "./exposure/exposure.csv"
            self.tables.append(
                (self.exposure.exposure_db, exposure_output_path, {"index": False})
            )

            # Store the exposure settings in the config file.
            self.config["exposure"] = [
                {
                    "type": "vector",
                    "dbase_file": exposure_output_path,
                    "crs": self.exposure.crs,
                }
            ]

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

        for name, df in self.tables:
            # Vulnerability
            if name == "vulnerability":
                fn = self.get_config(
                    "vulnerability.dbase_file", 
                    "vulnerability/vulnerability_curves.csv"
                )
                kwargs = {"index": False, "header": False}
            # Exposure
            elif name == "exposure":
                fn = self.get_config("exposure.dbase_file", "exposure/exposure.csv")
                kwargs = {"index": False}
            # Other, can also return an error or pass silently
            # I added vulnerability_identifiers here as it is required input for exposure
            else: 
                fn = f"{name}.csv"
                kwargs = dict()
            # make dir and save file
            self.logger.info(f"Writing model {name} table file to {fn}.")
            path = Path(self.root) / fn
            if not path.parent.is_dir():
                path.parent.mkdir(parents=True)
            
            if path.name.endswith("csv"):
                df.to_csv(path, **kwargs)
            elif path.name.endswith("xlsx"):
                df.to_excel(path, **kwargs)


    def _configwrite(self, fn):
        """Write config to Delft-FIAT configuration toml file."""
        # Save the configuration file.
        Config().save(self.config, Path(self.root).joinpath("settings.toml"))


    # FIAT specific attributes and methods
    @property
    def vulnerability(self) -> Vulnerability:
        """Returns a Vulnerability object from self.tables."""
        vf = Vulnerability()
        if "vulnerability" in self.tables:
            vf = vf.from_table(self.tables["vulnerability"])
        return vf
    
    @property
    def vf_ids_and_linking_df(self) -> pd.DataFrame:
        """Returns a dataframe with the vulnerability identifiers and linking."""
        if "vulnerability_identifiers" in self.tables:
            vi = self.tables["vulnerability_identifiers"]
        else:
            vi = pd.DataFrame()
        return vi