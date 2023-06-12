"""Implement fiat model class"""

from hydromt.models.model_grid import GridModel
import logging
import geopandas as gpd
import pandas as pd
import hydromt
from pathlib import Path
from os.path import join, basename
import glob

from shapely.geometry import box
from typing import Union, List

from .config import Config
from .workflows.vulnerability import Vulnerability
from .workflows.exposure_vector import ExposureVector
from .workflows.social_vulnerability_index import SocialVulnerabilityIndex
from .workflows.hazard import *

# from hydromt_sfincs import SfincsModel

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
        self._tables = dict()  # Dictionary of tables to write
        self.exposure = None

    def setup_global_settings(self, crs: str):
        """Setup Delft-FIAT global settings.

        Parameters
        ----------
        crs : str
            The CRS of the model.
        """
        self.set_config("global.crs", crs)

    def setup_output(
        self,
        output_dir: str = "output",
        output_csv_name: str = "output.csv",
        output_vector_name: Union[str, List[str]] = "spatial.gpkg",
    ) -> None:
        """Setup Delft-FIAT output folder and files.

        Parameters
        ----------
        output_dir : str, optional
            The name of the output directory, by default "output".
        output_csv_name : str, optional
            The name of the output csv file, by default "output.csv".
        output_vector_name : Union[str, List[str]], optional
            The name of the output vector file, by default "spatial.gpkg".
        """
        self.set_config("output", output_dir)
        self.set_config("output.csv.name", output_csv_name)
        if isinstance(output_vector_name, str):
            output_vector_name = [output_vector_name]
        for i, name in enumerate(output_vector_name):
            self.set_config(f"output.vector.name{str(i+1)}", name)

    def setup_basemaps(
        self,
        region,
        **kwargs,
    ):
        # FIXME Mario will update this function according to the one in Habitat
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

        # Set the region crs
        if geom.crs:
            self.region.set_crs(geom.crs)
        else:
            self.region.set_crs(4326)

    def setup_vulnerability(
        self,
        vulnerability_fn: Union[str, Path],
        vulnerability_identifiers_and_linking_fn: Union[str, Path],
        unit: str,
        functions_mean: Union[str, List[str], None] = "default",
        functions_max: Union[str, List[str], None] = None,
    ) -> None:
        """Setup the vulnerability curves from various possible inputs.

        Parameters
        ----------
        vulnerability_fn : Union[str, Path]
            The (relative) path or ID from the data catalog to the source of the
            vulnerability functions.
        vulnerability_identifiers_and_linking_fn : Union[str, Path]
            The (relative) path to the table that links the vulnerability functions and
            exposure categories.
        unit : str
            The unit of the vulnerability functions.
        functions_mean : Union[str, List[str], None], optional
            The name(s) of the vulnerability functions that should use the mean hazard
            value when using the area extraction method, by default "default" (this
            means that all vulnerability functions are using mean).
        functions_max : Union[str, List[str], None], optional
            The name(s) of the vulnerability functions that should use the maximum
            hazard value when using the area extraction method, by default None (this
            means that all vulnerability functions are using mean).
        """

        # Read the vulnerability data
        df_vulnerability = self.data_catalog.get_dataframe(vulnerability_fn)

        # Read the vulnerability linking table
        vf_ids_and_linking_df = self.data_catalog.get_dataframe(
            vulnerability_identifiers_and_linking_fn
        )

        # Process the vulnerability data
        vulnerability = Vulnerability(
            unit,
            self.logger,
        )

        # Depending on what the input is, another function is chosen to generate the
        # vulnerability curves file for Delft-FIAT.
        vulnerability.get_vulnerability_functions_from_one_file(
            df_source=df_vulnerability,
            df_identifiers_linking=vf_ids_and_linking_df,
        )

        # Set the area extraction method for the vulnerability curves
        vulnerability.set_area_extraction_methods(
            functions_mean=functions_mean, functions_max=functions_max
        )

        # Add the vulnerability curves to tables property
        self.set_tables(df=vulnerability.get_table(), name="vulnerability_curves")

        # Also add the identifiers
        self.set_tables(df=vf_ids_and_linking_df, name="vulnerability_identifiers")

        # Update config
        self.set_config(
            "vulnerability.file", "./vulnerability/vulnerability_curves.csv"
        )

    def setup_exposure_vector(
        self,
        asset_locations: Union[str, Path],
        occupancy_type: Union[str, Path],
        max_potential_damage: Union[str, Path],
        ground_floor_height: Union[int, float, str, Path, None],
        ground_floor_height_unit: str,
        occupancy_type_field: Union[str, None] = None,
        extraction_method: str = "centroid",
    ) -> None:
        """Setup vector exposure data for Delft-FIAT.

        Parameters
        ----------
        asset_locations : Union[str, Path]
            The path to the vector data (points or polygons) that can be used for the
            asset locations.
        occupancy_type : Union[str, Path]
            The path to the data that can be used for the occupancy type.
        max_potential_damage : Union[str, Path]
            The path to the data that can be used for the maximum potential damage.
        ground_floor_height : Union[int, float, str, Path None]
            Either a number (int or float), to give all assets the same ground floor
            height or a path to the data that can be used to add the ground floor
            height to the assets.
        ground_floor_height_unit : str
            The unit of the ground_floor_height
        occupancy_type_field : Union[str, None], optional
            The name of the field in the occupancy type data that contains the
            occupancy type, by default None (this means that the occupancy type data
            only contains one column with the occupancy type).
        extraction_method : str, optional
            The method that should be used to extract the hazard values from the
            hazard maps, by default "centroid".
        """
        self.exposure = ExposureVector(self.data_catalog, self.logger, self.region)

        if asset_locations == occupancy_type == max_potential_damage:
            # The source for the asset locations, occupancy type and maximum potential
            # damage is the same, use one source to create the exposure data.
            self.exposure.setup_from_single_source(
                asset_locations, ground_floor_height, extraction_method
            )
        else:
            # The source for the asset locations, occupancy type and maximum potential
            # damage is different, use three sources to create the exposure data.
            self.exposure.setup_from_multiple_sources(
                asset_locations,
                occupancy_type,
                max_potential_damage,
                ground_floor_height,
                extraction_method,
                occupancy_type_field,
            )

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

        # Add to tables
        self.set_tables(df=self.exposure.exposure_db, name="exposure")

        # Add to the geoms
        self.set_geoms(
            geom=self.exposure.get_geom_gdf(
                self._tables["exposure"], self.exposure.crs
            ),
            name="exposure",
        )

        # Update config
        self.set_config("exposure.vector.csv", "./exposure/exposure.csv")
        self.set_config("exposure.vector.crs", self.exposure.crs)
        self.set_config(
            "exposure.vector.file1", "./exposure/exposure.gpkg"
        )  # TODO: update if we have more than one file

    def setup_exposure_raster(self):
        """Setup raster exposure data for Delft-FIAT.
        This function will be implemented at a later stage.
        """
        NotImplemented

    def setup_hazard(
        self,
        map_fn: str,
        map_type: str,
        rp: str,
        crs: Union[int, str],
        nodata: Union[int, None],
        var: int,
        chunks: Union[int, str],
        risk_output: bool = True,
        hazard_type: str = "flooding",
        name_catalog: str = "flood_maps",
        maps_id: str = "RP",
    ):
        """_summary_

        Parameters
        ----------
        map_fn : str
            _description_
        map_type : str
            _description_
        rp : str
            _description_
        crs : Union[int, str]
            _description_
        nodata : Union[int, None]
            _description_
        var : int
            _description_
        chunks : Union[int,str]
            _description_
        risk_output : bool, optional
            _description_, by default True
        hazard_type : str, optional
            _description_, by default "flooding"
        name_catalog : str, optional
            _description_, by default "flood_maps"
        maps_id : str, optional
            _description_, by default "RP"
        """

        params_lists, params = get_parameters(
            map_fn,
            map_type,
            chunks,
            rp,
            crs,
            nodata,
            var,
        )

        check_parameters(
            params_lists,
            params,
            self,
        )

        list_names = []
        for idx, da_map_fn in enumerate(params_lists["map_fn_lst"]):
            kwargs, da_name, da_map_fn, da_type = read_floodmaps(
                list_names, da_map_fn, idx, params_lists, params
            )
            da = load_floodmaps(self, da_map_fn, name_catalog, da_name, **kwargs)

            # # reading from path
            # if da_map_fn.stem:
            #     if da_map_fn.stem == "sfincs_map":
            #         sfincs_root = os.path.dirname(da_map_fn)
            #         sfincs_model = SfincsModel(sfincs_root, mode="r")
            #         sfincs_model.read_results()
            #         result_list = list(sfincs_model.results.keys())
            #         sfincs_model.write_raster("results.zsmax", compress="LZW")
            #         da =  sfincs_model.results['zsmax']
            #         da.encoding["_FillValue"] = None
            #     else:
            #         if not self.region.empty:
            #             da = self.data_catalog.get_rasterdataset(da_map_fn, geom=self.region, **kwargs)
            #         else:
            #             da = self.data_catalog.get_rasterdataset(da_map_fn, **kwargs)
            # # reading from the datacatalog
            # else:
            #     if not self.region.empty:
            #         da = self.data_catalog.get_rasterdataset(name_catalog, variables=da_name, geom=self.region)
            #     else:
            #         da = self.data_catalog.get_rasterdataset(name_catalog, variables=da_name)

            da_rp, list_rp = checking_floodmaps(
                risk_output,
                self,
                da,
                da_name,
                da_map_fn,
                da_type,
                idx,
                params_lists,
                params,
                **kwargs,
            )
            self.set_config(
                "hazard",
                da_type,
                da_name,
                {
                    "usage": "True",
                    "map_fn": str(da_map_fn),
                    "map_type": str(da_type),
                    "rp": str(da_rp),
                    "crs": str(da.raster.crs),
                    "nodata": str(da.raster.nodata),
                    # "var": None if "var_lst" not in locals() else self.var_lst[idx],
                    "var": None
                    if "var_lst" not in params_lists
                    else str(params_lists["var_lst"][idx]),
                    "chunks": "auto"
                    if chunks == "auto"
                    else str(params_lists["chunks_lst"][idx]),
                },
            )

            self.set_maps(da, da_name)
            post = f"(rp {da_rp})" if risk_output else ""
            self.logger.info(f"Added {hazard_type} hazard map: {da_name} {post}")

        if risk_output:
            maps = self.maps
            list_keys = list(maps.keys())
            maps_0 = maps[list_keys[0]].rename("risk")
            list_keys.pop(0)

            for idx, x in enumerate(list_keys):
                key_name = list_keys[idx]
                layer = maps[key_name]
                maps_0 = xr.concat([maps_0, layer], dim="rp")

            new_da = maps_0.to_dataset(name="RISK")
            new_da.attrs = {
                "returnperiod": list(list_rp),
                "type": params_lists["map_type_lst"],
                "name": list_names,
                "Analysis": "Risk",
            }

            self.hazard = new_da
            self.set_maps(self.hazard, "HydroMT_Fiat_hazard")

            list_maps = list(self.maps.keys())

            if risk_output:
                for item in list_maps[:-1]:
                    self.maps.pop(item)

        # self.set_config(
        #     "hazard",
        #     {
        #         "file": [str(Path("hazard") / (self.maps[hazard_map].name + ".nc")) for hazard_map in self.maps.keys()]
        #     }

        # )

        # # Store the hazard settings.
        # hazard_settings = {}
        # hazard_maps = []
        # for hazard_map in self.maps.keys():
        #     hazard_maps.append(
        #         str(Path("hazard") / (self.maps[hazard_map].name + ".nc"))
        #     )

        # hazard_settings["grid_file"] = hazard_maps

        # if not isinstance(rp, list):
        #     rp = "Event"
        # hazard_settings["return_period"] = rp

        # hazard_settings["crs"] = hazard.crs
        # hazard_settings["spatial_reference"] = map_type
        # self.config["hazard"] = hazard_settings

    def setup_social_vulnerability_index(
        self, census_key: str, path: Union[str, Path], state_abbreviation: str
    ):
        """Setup the social vulnerability index for the vector exposure data for
        Delft-FIAT.

        Parameters
        ----------
        census_key : str
            The user's unique Census key that they got from the census.gov website
            (https://api.census.gov/data/key_signup.html) to be able to download the
            Census data
        path : str
            The path to the codebook excel
        state_abbreviation : str
            The abbreviation of the US state one would like to use in the analysis
        """
        # TODO: Read the SVI table

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

        # TODO: JOIN WITH GEOMETRIES. FOR MAPPING.
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
        """Parse Delft-FIAT configuration toml file to dict."""
        # Read the fiat configuration toml file.
        config = Config()
        return config.load_file(fn)

    def check_path_exists(self, fn):
        """TODO: decide to use this or another function (check_file_exist in py)"""
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
        vulnerability_fn = Path(self.root) / self.get_config("vulnerability.dbase_file")
        if Path(vulnerability_fn).is_file():
            self.logger.debug(f"Reading vulnerability table {vulnerability_fn}")
            self.vulnerability = Vulnerability(fn=vulnerability_fn)
            self._tables["vulnerability_curves"] = self.vulnerability.get_table()
        else:
            logging.warning(f"File {vulnerability_fn} does not exist!")

        # Now with exposure
        exposure_fn = Path(self.root) / self.get_config("exposure.dbase_file")
        if Path(exposure_fn).is_file():
            self.logger.debug(f"Reading exposure table {exposure_fn}")
            self.exposure = ExposureVector(crs=self.get_config("exposure.crs"))
            self.exposure.read(exposure_fn)
            self._tables["exposure"] = self.exposure.exposure_db
        else:
            logging.warning(f"File {exposure_fn} does not exist!")

        # If needed read other tables files like vulnerability identifiers
        # Comment if not needed - I usually use os rather than pathlib, change if you prefer
        fns = glob.glob(join(self.root, "*.csv"))
        if len(fns) > 0:
            for fn in fns:
                self.logger.info(f"Reading table {fn}")
                name = basename(fn).split(".")[0]
                tbl = pd.read_csv(fn)
                self.set_tables(tbl, name=name)

    def write(self):
        """Method to write the complete model schematization and configuration to file."""
        self.logger.info(f"Writing model data to {self.root}")

        if self.config:  # try to read default if not yet set
            self.write_config()
        if self.maps:
            self.write_maps(fn="hazard/{name}.nc")
        if self.geoms:
            self.write_geoms(fn="exposure/{name}.gpkg")
        if self._tables:
            self.write_tables()

    def write_tables(self) -> None:
        if len(self._tables) == 0:
            self.logger.debug("No table data found, skip writing.")
            return
        self._assert_write_mode

        for name in self._tables.keys():
            # Vulnerability
            if name == "vulnerability_curves":
                # The default location and save settings of the vulnerability curves
                fn = "vulnerability/vulnerability_curves.csv"
                kwargs = {"index": False, "header": False}
            # Exposure
            elif name == "exposure":
                # The default location and save settings of the exposure data
                fn = "exposure/exposure.csv"
                kwargs = {"index": False}
            elif name == "vulnerability_identifiers":
                # The default location and save settings of the vulnerability curves
                fn = "vulnerability/vulnerability_identifiers.csv"
                kwargs = dict()
            # Other, can also return an error or pass silently
            else:
                fn = f"{name}.csv"
                kwargs = dict()

            # make dir and save file
            self.logger.info(f"Writing model {name} table file to {fn}.")
            path = Path(self.root) / fn
            if not path.parent.is_dir():
                path.parent.mkdir(parents=True)

            if path.name.endswith("csv"):
                self._tables[name].to_csv(path, **kwargs)
            elif path.name.endswith("xlsx"):
                self._tables[name].to_excel(path, **kwargs)

    def _configwrite(self, fn):
        """Write config to Delft-FIAT configuration toml file."""
        # Save the configuration file.
        Config().save(self.config, Path(self.root).joinpath("settings.toml"))

    # FIAT specific attributes and methods
    @property
    def vulnerability_curves(self) -> pd.DataFrame:
        """Returns a dataframe with the damage functions."""
        if "vulnerability_curves" in self._tables:
            vf = self._tables["vulnerability_curves"]
        else:
            vf = pd.DataFrame()
        return vf

    @property
    def vf_ids_and_linking_df(self) -> pd.DataFrame:
        """Returns a dataframe with the vulnerability identifiers and linking."""
        if "vulnerability_identifiers" in self._tables:
            vi = self._tables["vulnerability_identifiers"]
        else:
            vi = pd.DataFrame()
        return vi

    def set_tables(self, df: pd.DataFrame, name: str) -> None:
        """Add <pandas.DataFrame> to the tables variable.

        Parameters
        ----------
        df : pd.DataFrame
            New DataFrame to add
        name : str
            Name of the DataFrame to add
        """
        if not (isinstance(df, pd.DataFrame) or isinstance(df, pd.Series)):
            raise ValueError("df type not recognized, should be pandas.DataFrame.")
        if name in self._tables:
            if not self._write:
                raise IOError(f"Cannot overwrite table {name} in read-only mode")
            elif self._read:
                self.logger.warning(f"Overwriting table: {name}")
        self._tables[name] = df
