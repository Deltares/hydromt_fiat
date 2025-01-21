"""Implement fiat model class"""

import csv
import glob
import logging
import os
from pathlib import Path
from typing import List, Optional, Union
import xarray as xr
import geopandas as gpd
import hydromt
import pandas as pd
import tomli
import tomli_w
from hydromt.models.model_grid import GridModel
from pyproj.crs import CRS
from shapely.geometry import box
import shutil
from shapely.geometry import box
import tempfile

from hydromt.raster import full_from_transform
from hydromt_fiat.api.data_types import Units
from hydromt_fiat.util import DATADIR
from hydromt_fiat.spatial_joins import SpatialJoins
from hydromt_fiat.workflows.exposure_vector import ExposureVector
from hydromt_fiat.workflows.hazard import (
    create_lists,
    check_lists_size,
    read_maps,
    check_maps_metadata,
    check_maps_rp,
    check_map_uniqueness,
    create_risk_dataset,
)
from hydromt_fiat.workflows.equity_data import EquityData
from hydromt_fiat.workflows.social_vulnerability_index import (
    SocialVulnerabilityIndex,
    list_of_states,
)
from hydromt_fiat.workflows.vulnerability import Vulnerability
from hydromt_fiat.workflows.aggregation_areas import join_exposure_aggregation_areas
from hydromt_fiat.workflows.building_footprints import join_exposure_building_footprints
from hydromt_fiat.workflows.gis import locate_from_exposure
from hydromt_fiat.workflows.utils import get_us_county_numbers
from hydromt_fiat.workflows.utils import rename_geoid_short
from hydromt_fiat.api.data_types import Currency

__all__ = ["FiatModel"]

_logger = logging.getLogger(__name__)


class FiatModel(GridModel):
    """General and basic API for the FIAT model in hydroMT."""

    _NAME = "fiat"
    _CONF = "settings.toml"
    _GEOMS = {}  # FIXME Mapping from hydromt names to model specific names
    _MAPS = {}  # FIXME Mapping from hydromt names to model specific names
    _FOLDERS = ["hazard", "exposure", "vulnerability", "output"]
    _CLI_ARGS = {"region": "setup_region"}
    _DATADIR = DATADIR

    def __init__(
        self,
        root=None,
        mode="w",
        config_fn=None,
        data_libs=None,
        logger=_logger,
    ):
        # Add the global catalog (tables etc.) to the data libs by default
        if data_libs is None:
            data_libs = []
        if not isinstance(data_libs, (list, tuple)):
            data_libs = [data_libs]
        data_libs += [Path(DATADIR, "hydromt_fiat_catalog_global.yml")]
        super().__init__(
            root=root,
            mode=mode,
            config_fn=config_fn,
            data_libs=data_libs,
            logger=logger,
        )
        self._tables = dict()  # Dictionary of tables to write
        self.exposure = None
        self.vulnerability = None
        self.vf_ids_and_linking_df = pd.DataFrame()
        self.spatial_joins = dict(
            aggregation_areas=None, additional_attributes=None
        )  # Dictionary containing all the spatial join metadata

        self.building_footprint_fn = ""  # Path to the building footprints dataset
        self.building_footprint = gpd.GeoDataFrame()  # building footprints dataset

    def __del__(self):
        """Close the model and remove the logger file handler."""
        for handler in self.logger.handlers:
            if (
                isinstance(handler, logging.FileHandler)
                and "hydromt.log" in handler.baseFilename
            ):
                handler.close()
                self.logger.removeHandler(handler)

    def setup_global_settings(
        self,
        crs: str = None,
        gdal_cache: int = None,
        keep_temp_files: bool = None,
        thread: int = None,
        chunk: List[int] = None,
    ) -> None:
        """Setup Delft-FIAT global settings.

        Parameters
        ----------
        crs : str
            The CRS of the model.
        """
        if crs:
            self.set_config("global.crs", f"EPSG:{crs}")
        if gdal_cache:
            self.set_config("global.gdal_cache", gdal_cache)
        if keep_temp_files:
            self.set_config("global.keep_temp_files", keep_temp_files)
        if thread:
            self.set_config("global.thread", thread)
        if chunk:
            self.set_config("global.grid.chunk", chunk)

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
        self.set_config("output.path", output_dir)
        self.set_config("output.csv.name", output_csv_name)
        if isinstance(output_vector_name, str):
            output_vector_name = [output_vector_name]
        for i, name in enumerate(output_vector_name):
            self.set_config(f"output.geom.name{str(i+1)}", name)

    def setup_region(
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
        self.set_geoms(geom.dissolve(), "region")

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
        step_size: Optional[float] = None,
        continent: Optional[str] = None,
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
            value when using the area extract_method, by default "default" (this
            means that all vulnerability functions are using mean).
        functions_max : Union[str, List[str], None], optional
            The name(s) of the vulnerability functions that should use the maximum
            hazard value when using the area extract_method, by default None (this
            means that all vulnerability functions are using mean).
        """

        # Read the vulnerability data
        df_vulnerability = self.data_catalog.get_dataframe(vulnerability_fn)

        # Read the vulnerability linking table
        self.vf_ids_and_linking_df = self.data_catalog.get_dataframe(
            vulnerability_identifiers_and_linking_fn
        )

        # If the JRC vulnerability curves are used, the continent needs to be specified
        if (
            vulnerability_identifiers_and_linking_fn
            == "jrc_vulnerability_curves_linking"
        ):
            assert (
                continent is not None
            ), "Please specify the continent when using the JRC vulnerability curves."
            self.vf_ids_and_linking_df["continent"] = continent.lower()
            unit = Units.meters.value

        # Process the vulnerability data
        self.vulnerability = Vulnerability(
            unit,
            self.logger,
        )

        # Depending on what the input is, another function is ran to generate the
        # vulnerability curves file for Delft-FIAT.
        self.vulnerability.get_vulnerability_functions_from_one_file(
            df_source=df_vulnerability,
            df_identifiers_linking=self.vf_ids_and_linking_df,
            continent=continent,
        )

        # Set the area extract_method for the vulnerability curves
        self.vulnerability.set_area_extraction_methods(
            functions_mean=functions_mean, functions_max=functions_max
        )

        # Update config
        self.set_config("vulnerability.file", "vulnerability/vulnerability_curves.csv")
        self.set_config("vulnerability.unit", unit)

        if step_size:
            self.set_config("vulnerability.step_size", step_size)

    def setup_vulnerability_from_csv(self, csv_fn: Union[str, Path], unit: str) -> None:
        """Setup the vulnerability curves from one or multiple csv files.

        Parameters
        ----------
            csv_fn : str
                The full path to the folder which holds the single vulnerability curves.
            unit : str
                The unit of the water depth column for all vulnerability functions
                (e.g. meter).
        """
        # Process the vulnerability data
        if not self.vulnerability:
            self.vulnerability = Vulnerability(
                unit,
                self.logger,
            )
        self.vulnerability.from_csv(csv_fn)

    def setup_road_vulnerability(
        self,
        vertical_unit: str,
        threshold_value: float = 0.6,
        min_hazard_value: float = 0,
        max_hazard_value: float = 10,
        step_hazard_value: float = 1.0,
    ):
        if not self.vulnerability:
            self.vulnerability = Vulnerability(
                vertical_unit,
                self.logger,
            )
        self.vulnerability.create_step_function(
            "roads",
            threshold_value,
            min_hazard_value,
            max_hazard_value,
            step_hazard_value,
        )

    def setup_population_vulnerability(
        self,
        vertical_unit: str,
        threshold_value: float = 0.4,
        min_hazard_value: float = 0,
        max_hazard_value: float = 10,
        step_hazard_value: float = 1.0,
    ):
        if not self.vulnerability:
            self.vulnerability = Vulnerability(
                vertical_unit,
                self.logger,
            )
        self.vulnerability.create_step_function(
            "population",
            threshold_value,
            min_hazard_value,
            max_hazard_value,
            step_hazard_value,
        )

    def setup_exposure_buildings(
        self,
        asset_locations: Union[str, Path],
        occupancy_type: Union[str, Path],
        max_potential_damage: Union[str, Path],
        ground_floor_height: Union[int, float, str, Path, None],
        unit: Units = None,
        gfh_unit: Units = None,
        gfh_attribute_name: str = None,
        occupancy_attr: Union[str, None] = None,
        occupancy_object_type: Union[str, List[str]] = None,
        extraction_method: str = "centroid",
        damage_types: List[str] = ["structure", "content"],
        damage_unit: Currency = Currency.dollar.value,
        country: Union[str, None] = None,
        ground_elevation: Union[int, float, str, Path, None] = None,
        grnd_elev_unit: Units = None,
        bf_conversion: bool = False,
        keep_unclassified: bool = True,
        dst_crs: Union[str, None] = None,
        damage_translation_fn: Union[Path, str] = None,
        eur_to_us_dollar: bool = False,
    ) -> None:
        """Setup building exposure (vector) data for Delft-FIAT.

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
        unit : Units
            The unit of the model
        gfh_unit : Units
            The unit of the ground_floor_height
        gfh_attribute_name : str
            The attribute name to be used to set the ground_flht. If None, the
            attribute name will be set to 'ground_floor_height'.
        occupancy_attr : Union[str, None], optional
            The name of the field in the occupancy type data that contains the
            occupancy type, by default None (this means that the occupancy type data
            only contains one column with the occupancy type).
        extraction_method : str, optional
            The method that should be used to extract the hazard values from the
            hazard maps, by default "centroid".
        damage_types : Union[List[str], None], optional
            The damage types that should be used for the exposure data, by default
            ["structure", "content"]. The damage types are used to link the
            vulnerability functions to the exposure data.
        damage_unit: Currency, optional
            The currency/unit of the Damage data, default in USD $
        country : Union[str, None], optional
            The country that is used for the exposure data, by default None. This is
            only required when using the JRC vulnerability curves.
        ground_elevation: Union[int, float, str, Path None]
            Either a number (int or float), to give all assets the same ground elevation or a path to the data that can be used to add the elevation to the assets.
        grnd_elev_unit : Units
            The unit of the ground_elevation
        bf_conversion: bool, optional
            If building footprints shall be converted into point data.
        keep_unclassified: bool, optional
            Whether building footprints without classification are removed or reclassified as "residential"
        dst_crs : Union[str, None], optional
            The destination crs of the exposure geometries. if not provided,
            it is taken from the region attribute of `FiatModel`. By default None
        damage_translation_fn: Union[Path, str], optional
            The path to the translation function that can be used to relate user damage curves with user damages.
        eur_to_us_dollar: bool
            Convert JRC Damage Values (Euro 2010) into US-Dollars (2025)
        """
        # In case the unit is passed as a pydantic value get the string
        if hasattr(unit, "value"):
            unit = unit.value

        self.exposure = ExposureVector(
            self.data_catalog,
            self.logger,
            self.region,
            unit=unit,
            damage_unit=damage_unit,
        )

        if asset_locations == max_potential_damage:
            # The source for the asset locations, occupancy type and maximum potential
            # damage is the same, use one source to create the exposure data.
            self.exposure.setup_buildings_from_single_source(
                asset_locations,
                ground_floor_height,
                extraction_method,
                ground_elevation=ground_elevation,
                eur_to_us_dollar = eur_to_us_dollar
            )

        else:
            # The source for the asset locations, occupancy type and maximum potential
            # damage is different, use three sources to create the exposure data.
            # Setup exposure buildings
            self.exposure.setup_buildings_from_multiple_sources(
                asset_locations,
                occupancy_type,
                max_potential_damage,
                ground_floor_height,
                extraction_method,
                occupancy_attr,
                damage_types=damage_types,
                country=country,
                gfh_unit=gfh_unit,
                ground_elevation=ground_elevation,
                grnd_elev_unit=grnd_elev_unit,
                bf_conversion=bf_conversion,
                keep_unclassified=keep_unclassified,
                damage_translation_fn=damage_translation_fn,
                gfh_attribute_name=gfh_attribute_name,
                eur_to_us_dollar = eur_to_us_dollar,
            )

        if (asset_locations != occupancy_type) and occupancy_object_type is not None:
            self.exposure.setup_occupancy_type(
                occupancy_source=occupancy_type,
                occupancy_attr=occupancy_attr,
                type_add=occupancy_object_type,
                keep_unclassified=keep_unclassified,
            )

        # Link the damage functions to assets
        try:
            assert not self.vf_ids_and_linking_df.empty
        except AssertionError:
            self.logger.error(
                "Please call the 'setup_vulnerability' function before "
                "the 'setup_exposure_buildings' function. Error message: {e}"
            )
        self.exposure.link_exposure_vulnerability(
            self.vf_ids_and_linking_df, damage_types
        )

        # Set building footprints
        if bf_conversion:
            self.bf_spatial_joins()
            attrs = {
                "name": "BF_FID",
                "file": "geoms/building_footprints/building_footprints.geojson",
                "field_name": "BF_FID",  # TODO check how and where this is defined
            }
            if not self.spatial_joins["additional_attributes"]:
                self.spatial_joins["additional_attributes"] = []
            self.spatial_joins["additional_attributes"].append(attrs)

        # Check for the required columns
        self.exposure.check_required_columns()

        # Possibly reproject according to destination crs
        src_crs = CRS.from_user_input(self.exposure.crs)
        crs = None
        try:
            crs = CRS.from_user_input(dst_crs)
        except BaseException:
            if self.region is not None:
                crs = self.region.crs

        while True:
            if crs is None:
                break
            if crs.to_authority() == src_crs.to_authority():
                break
            for item in self.exposure.exposure_geoms:
                item.to_crs(crs, inplace=True)
            self.exposure.crs = ":".join(crs.to_authority())
            break

        # Update the other config settings
        self.set_config("exposure.csv.file", "exposure/exposure.csv")
        self.set_config("exposure.geom.crs", self.exposure.crs)
        self.set_config("exposure.geom.unit", unit)
        self.set_config("exposure.damage_unit", damage_unit)

    def setup_exposure_roads(
        self,
        roads_fn: Union[str, Path],
        road_damage: Union[str, Path, int, float],
        road_types: Union[str, List[str], bool] = True,
        unit: str = "meters",
    ):
        """Setup road exposure data for Delft-FIAT.

        Parameters
        ----------
        roads_fn : Union[str, Path]
            Path to the road network source (e.g., OSM) or file.
        road_types : Union[str, List[str], bool], optional
            List of road types to include in the exposure data, by default True
        """
        if not self.exposure:
            self.exposure = ExposureVector(
                self.data_catalog,
                self.logger,
                self.region,
                unit=unit,
            )
        self.exposure.setup_roads(roads_fn, road_damage, road_types)

        # Link to vulnerability curves

        # Combine the exposure database with pre-existing exposure data if available

    def setup_exposure_population(
        self,
        impacted_population_fn: Union[
            int, float, str, Path, List[str], List[Path], pd.DataFrame
        ] = None,
        attribute_name: Union[str, List[str], None] = None,
        method_impacted_pop: Union[str, List[str], None] = "intersection",
        max_dist: float = 10,
        unit: str = "meters",
    ) -> None:
        if not self.exposure:
            self.exposure = ExposureVector(
                self.data_catalog,
                self.logger,
                self.region,
                unit=unit,
            )
        self.exposure.setup_impacted_population(
            impacted_population_fn, attribute_name, method_impacted_pop, max_dist
        )

        self.set_config("exposure.types", ["damages", "affected"])

    def bf_spatial_joins(self):
        self.building_footprint = self.exposure.building_footprints
        self.building_footprint["BF_FID"] = [
            i for i in range(1, len(self.building_footprint) + 1)
        ]
        BF_exposure_gdf = self.exposure.get_full_gdf(self.exposure.exposure_db).merge(
            self.building_footprint[["object_id", "BF_FID"]], on="object_id"
        )
        del BF_exposure_gdf["geometry"]
        del self.building_footprint["object_id"]
        self.exposure.exposure_db = BF_exposure_gdf

    def update_ground_floor_height(
        self,
        source: Union[int, float, str, Path, None],
        gfh_attribute_name: str = None,
        gfh_method: Union[str, List[str], None] = "nearest",
        gfh_unit: Units = None,
        max_dist: float = 10,
    ):
        if self.exposure:
            self.exposure.setup_ground_floor_height(
                source, gfh_attribute_name, gfh_method, max_dist, gfh_unit
            )

    def update_max_potential_damage(
        self,
        source: Union[
            int, float, str, Path, List[str], List[Path], pd.DataFrame
        ] = None,
        damage_types: Union[List[str], str, None] = None,
        country: Union[str, None] = None,
        attribute_name: Union[str, List[str], None] = None,
        method_damages: Union[str, List[str], None] = "nearest",
        max_dist: float = 10,
        eur_to_us_dollar: bool = False
    ):
        if self.exposure:
            self.exposure.setup_max_potential_damage(
                max_potential_damage=source,
                damage_types=damage_types,
                country=country,
                attribute_name=attribute_name,
                method_damages=method_damages,
                max_dist=max_dist,
                eur_to_us_dollar = eur_to_us_dollar
            )

    def update_ground_elevation(
        self, source: Union[int, float, None, str, Path], grnd_elev_unit: Units
    ):
        if self.exposure:
            self.exposure.setup_ground_elevation(source, grnd_elev_unit)

    def setup_exposure_raster(self):
        """Setup raster exposure data for Delft-FIAT.
        This function will be implemented at a later stage.
        """
        NotImplemented

    def setup_hazard(
        self,
        map_fn: Union[str, Path, list[str], list[Path]],
        map_type: Union[str, list[str]],
        rp: Union[int, list[int], None] = None,
        crs: Union[int, str, list[int], list[str], None] = None,
        nodata: Union[int, list[int], None] = None,
        var: Union[str, list[str], None] = None,
        chunks: Union[int, str, list[int]] = "auto",
        hazard_type: str = "flooding",
        risk_output: bool = False,
        unit_conversion_factor: float = 1.0,
        clip_exposure: bool = False,
    ) -> None:
        """Set up hazard maps. This component integrates multiple checks for the hazard
        maps.

        Parameters
        ----------
        map_fn : Union[str, Path, list[str], list[Path]]
            The data catalog key or list of keys from where to retrieve the
            hazard maps. This can also be a path or list of paths to take files
            directly from a local database.
        map_type : Union[str, list[str]]
            The data type of each map speficied in map_fn. In case a single
            map type applies for all the elements a single string can be provided.
        rp : Union[int, list[int], None], optional.
            The return period (rp) type of each map speficied in map_fn in case a
            risk output is required. If the rp is not provided and risk
            output is required the workflow will try to retrieve the rp from the
            files's name, by default None.
        crs : Union[int, str, list[int], list[str], None], optional
            The projection (crs) required in EPSG code of each of the maps provided. In
            case a single crs applies for all the elements a single value can be
            provided as code or string (e.g. "EPSG:4326"). If not provided, then the crs
            will be taken from orginal maps metadata, by default None.
        nodata : Union[int, list[int], None], optional
            The no data values in the rasters arrays. In case a single no data applies
            for all the elements a single value can be provided as integer, by default
            None.
        var : Union[str, list[str], None], optional
            The name of the variable to be selected in case a netCDF file is provided
            as input, by default None.
        chunks : Union[int, str, list[int]], optional
            The chuck region per map. In case a single no data applies for all the
            elements a single value can be provided as integer. If "auto"is provided
            the auto setting will be provided by default "auto"
        hazard_type : str, optional
            Type of hazard to be studied, by default "flooding"
        risk_output : bool, optional
            The parameter that defines if a risk analysis is required, by default False
        clip_exposure : bool, optional
            The parameter that defines if the exposure dataset should be clipped by the hazard extent, by default False
        """
        # create lists of maps and their parameters to be able to iterate over them
        params = create_lists(map_fn, map_type, rp, crs, nodata, var, chunks)
        check_lists_size(params)

        rp_list = []
        map_name_lst = []

        for idx, da_map_fn in enumerate(params["map_fn_lst"]):
            # read maps and retrieve their attributes
            if isinstance(da_map_fn, os.PathLike) or isinstance(da_map_fn, str):
                # if path is provided read and load it as xarray
                da_map_fn, da_name, da_type = read_maps(params, da_map_fn, idx)
                da = self.data_catalog.get_rasterdataset(
                    da_map_fn
                )  # removed geom=self.region because it is not always there
            elif isinstance(da_map_fn, xr.DataArray):
                # if xarray is provided directly assign that
                da = da_map_fn
                da_name = "hazard_map"
                da_type = map_type
            else:
                raise ValueError(
                    "The hazard map provided should be a path like object or an DataArray"
                )
            # Convert to units of the exposure data if required
            if (
                self.exposure
            ):  # change to be sure that the unit information is available from the exposure dataset
                if hasattr(da, "units"):
                    if self.exposure.unit != da.units:
                        da = da * unit_conversion_factor

            # convert to gdal compliant
            da.encoding["_FillValue"] = None
            da = da.raster.gdal_compliant()

            # check masp projection, null data, and grids
            check_maps_metadata(self.staticmaps, params, da, da_name, idx)

            # check maps return periods
            da_rp = check_maps_rp(params, da, da_name, idx, risk_output)

            if risk_output and da_map_fn.stem == "sfincs_map":
                da_name = da_name + f"_{str(da_rp)}"

            post = f"(rp {da_rp})" if risk_output else ""
            self.logger.info(f"Added {hazard_type} hazard map: {da_name} {post}")

            rp_list.append(da_rp)
            map_name_lst.append(da_name)

            da = da.assign_attrs(
                {
                    "return_period": str(da_rp),
                    "type": da_type,
                    "name": da_name,
                    "analysis": "event",
                }
            )

            # Ensure that grid_mapping is deleted if it exists to avoid errors when making the gdal compliant netcdf
            if "grid_mapping" in da.encoding:
                del da.encoding["grid_mapping"]

            da = da.to_dataset(name=da_name)

            self.set_maps(da, da_name)

        check_map_uniqueness(map_name_lst)

        # in case of risk analysis, create a single netcdf with multibans per rp
        if risk_output:
            da, sorted_rp, sorted_names = create_risk_dataset(
                params, rp_list, map_name_lst, self.maps
            )

            self.set_grid(da)

            self.grid.attrs = {
                "rp": sorted_rp,
                "type": params[
                    "map_type_lst"
                ],  # TODO: This parameter has to be changed in case that a list with different hazard types per map is provided
                "name": sorted_names,
                "analysis": "risk",
            }

            # Ensure that grid_mapping is deleted if it exists to avoid errors when making the gdal compliant netcdf
            if "grid_mapping" in self.grid.encoding:
                del self.grid.encoding["grid_mapping"]

            list_maps = list(self.maps.keys())

            for item in list_maps[:]:
                self.maps.pop(item)

        # set configuration .toml file
        self.set_config(
            "hazard.return_periods", str(da_rp) if not risk_output else sorted_rp
        )

        self.set_config(
            "hazard.file",
            (
                [
                    str(Path("hazard") / (hazard_map + ".nc"))
                    for hazard_map in self.maps.keys()
                ][0]
                if not risk_output
                else [str(Path("hazard") / ("risk_map" + ".nc"))][0]
            ),
        )
        self.set_config(
            "hazard.crs",
            (
                [
                    "EPSG:" + str((self.maps[hazard_map].raster.crs.to_epsg()))
                    for hazard_map in self.maps.keys()
                ][0]
                if not risk_output
                else ["EPSG:" + str((self.crs.to_epsg()))][0]
            ),
        )

        self.set_config(
            "hazard.elevation_reference", "dem" if da_type == "water_depth" else "datum"
        )

        # Set the configurations for a multiband netcdf
        self.set_config(
            "hazard.settings.subset",
            (
                [(self.maps[hazard_map].name) for hazard_map in self.maps.keys()][0]
                if not risk_output
                else sorted_names
            ),
        )

        self.set_config(
            "hazard.settings.var_as_band",
            risk_output,
        )

        self.set_config(
            "hazard.risk",
            risk_output,
        )
        # Clip exposure to hazard map
        if clip_exposure:
            self.clip_exposure_to_hazard_extent(da)

    def clip_exposure_to_hazard_extent(self, floodmap: xr.DataArray = None):
        """Clip the exposure data to the bounding box of the hazard data.

        This method clips the exposure data to the bounding box of the hazard data. It creates a GeoDataFrame
        from the hazard polygons, and then uses the `gpd.clip` function to clip the exposure geometries to the
        bounding box of the hazard polygons. If the exposure data contains roads, it is split into two separate
        GeoDataFrames: one for buildings and one for roads. The clipped exposure data is then saved back to the
        `exposure_db` attribute of the `FiatModel` object.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        gdf = self.exposure.get_full_gdf(self.exposure.exposure_db)
        crs = gdf.crs
        floodmap = floodmap.rio.reproject(crs)
        fm_bounds = floodmap.raster.bounds
        fm_geom = box(*fm_bounds)

        # Clip the fiat region
        clipped_region = self.region.clip(fm_geom)
        self.geoms["region"] = clipped_region

        if not self.building_footprint.empty:
            # Clip the building footprints
            self.building_footprint = self.building_footprint[
                self.building_footprint["geometry"].within(fm_geom)
            ]
            bf_fid = self.building_footprint["BF_FID"]
            fieldname = "BF_FID"

        # Clip the exposure geometries
        # Filter buildings and roads
        if gdf["primary_object_type"].str.contains("road").any():
            gdf_roads = gdf[gdf["primary_object_type"].str.contains("road")]
            gdf_roads = gdf_roads[gdf_roads["geometry"].within(fm_geom)]
            gdf_buildings = gdf[~gdf["primary_object_type"].str.contains("road")]
            if not self.building_footprint.empty:
                gdf_buildings = self.check_bf_complete(
                    gdf_buildings, fieldname, clipped_region, bf_fid
                )
            else:
                gdf_buildings = gdf_buildings[gdf_buildings["geometry"].within(fm_geom)]
            idx_buildings = self.exposure.geom_names.index("buildings")
            idx_roads = self.exposure.geom_names.index("roads")
            self.exposure.exposure_geoms[idx_buildings] = gdf_buildings[
                ["object_id", "geometry"]
            ]
            self.exposure.exposure_geoms[idx_roads] = gdf_roads[
                ["object_id", "geometry"]
            ]
            gdf = pd.concat([gdf_buildings, gdf_roads])
        else:
            if not self.building_footprint.empty:
                gdf = self.check_bf_complete(gdf, fieldname, clipped_region, bf_fid)
            else:
                gdf = gdf[gdf["geometry"].within(fm_geom)]
            self.exposure.exposure_geoms[0] = gdf[["object_id", "geometry"]]

        # Save exposure dataframe
        del gdf["geometry"]
        self.exposure.exposure_db = gdf

    def check_bf_complete(
        self,
        gdf_exposure: gpd.GeoDataFrame,
        fieldname: str,
        clipped_region: gpd.GeoDataFrame,
        bf_fid: gpd.GeoDataFrame,
    ):
        """Checks whether all building points have a building footprint.

        This method checks if all points have a building footprint. If a point does not have a biulding footprint
        it will be concenated with the exposure gdf anyhow and not be filtered out. By this it is assured
        that even if a building footprint is not available on e.g. OSM, the exposure point does not get lost.

        Parameters
        ----------
        gdf_exposure: gpd.GeoDataFrame
            The GeoDataFrame that contains the full exposure (excl. roads).
        fieldname: str
            The fieldname of the building footprint.
        clipped_region: gpd.GeoDataFrame
            The clipped region.
        bf_fid: gpd.GeoDataFrame
            The GeoDataFrame of the building footprints.

        Returns
        -------
        gdf_buildings: GeoDataFrame
        """

        if gdf_exposure[fieldname].isna().any():
            gdf_building_points = gdf_exposure[gdf_exposure[fieldname].isna()]
            gdf_building_footprints = gdf_exposure[~gdf_exposure[fieldname].isna()]
            gdf_building_points_clipped = gdf_building_points[
                gdf_building_points["geometry"].within(
                    clipped_region["geometry"].union_all()
                )
            ]
            gdf_building_footprints_clipped = gdf_building_footprints[
                gdf_building_footprints[fieldname].isin(bf_fid)
            ]
            gdf_buildings = pd.concat(
                [gdf_building_points_clipped, gdf_building_footprints_clipped]
            )
        else:
            gdf_buildings = gdf_exposure[gdf_exposure[fieldname].isin(bf_fid)]

        return gdf_buildings

    def setup_social_vulnerability_index(
        self,
        census_key: str,
        codebook_fn: Union[str, Path],
        year_data: int = None,
        save_all: bool = False,
    ):
        """Setup the social vulnerability index for the vector exposure data for
        Delft-FIAT. This method has so far only been tested with US Census data
        but aims to be generalized to other datasets as well.

        Parameters
        ----------
        path_dataset : str
            The path to a predefined dataset
        census_key : str
            The user's unique Census key that they got from the census.gov website
            (https://api.census.gov/data/key_signup.html) to be able to download the
            Census data
        codebook_fn : Union[str, Path]
            The path to the codebook excel
        year_data: int
            The year of which the census data should be downloaded, 2020, 2021, or 2022
        save_all: bool
            If True, all (normalized) data variables are saved, if False, only the SVI
            column is added to the FIAT exposure data. By default False.
        """
        # Check if the exposure data exists
        if self.exposure:
            # First find the state(s) and county/counties where the exposure data is
            # located in
            us_states_counties = self.data_catalog.get_dataframe("us_states_counties")
            counties, states = locate_from_exposure(
                self.exposure.exposure_geoms[0]["geometry"]
            )
            states_dict = list_of_states()
            state_abbreviation = []
            for state in states:
                try:
                    state_abbreviation.append(states_dict[state])
                except KeyError:
                    self.logger.warning(f"State {state} not found.")

            county_numbers = get_us_county_numbers(counties, us_states_counties)

            # Create SVI object
            save_folder = str(Path(self.root) / "exposure" / "SVI")
            svi = SocialVulnerabilityIndex(self.data_catalog, self.logger, save_folder)

            # Call functionalities of SVI
            svi.set_up_census_key(census_key)
            svi.variable_code_csv_to_pd_df(codebook_fn)
            svi.set_up_download_codes()
            svi.set_up_state_code(state_abbreviation)
            svi.download_census_data(year_data)
            svi.rename_census_data("Census_code_withE", "Census_variable_name")
            svi.identify_no_data()
            svi.check_nan_variable_columns("Census_variable_name", "Indicator_code")
            svi.check_zeroes_variable_rows()
            translation_variable_to_indicator = svi.create_indicator_groups(
                "Census_variable_name", "Indicator_code"
            )
            svi.processing_svi_data(translation_variable_to_indicator)
            svi.normalization_svi_data()
            svi.domain_scores()
            svi.composite_scores()
            svi.match_geo_ID()
            svi.download_shp_geom(year_data, county_numbers)
            svi.merge_svi_data_shp()
            gdf = rename_geoid_short(svi.svi_data_shp)
            # store the relevant tables coming out of the social vulnerability module
            self.set_tables(
                df=gdf.drop(columns="geometry"), name="social_vulnerability_scores"
            )
            # TODO: Think about adding an indicator for missing data to the svi.svi_data_shp

            # Link the SVI score to the exposure data
            exposure_data = self.exposure.get_full_gdf(self.exposure.exposure_db)
            exposure_data.sort_values("object_id")

            if svi.svi_data_shp.crs != exposure_data.crs:
                svi.svi_data_shp.to_crs(crs=exposure_data.crs, inplace=True)

            if save_all:
                # Clean up the columns that are saved
                cols_to_save = list(svi.svi_data_shp.columns)
                cols_to_save.remove("GEO_ID")
                cols_to_save.remove("GEOID_short")
                cols_to_save.remove("NAME")
                cols_to_save.remove("composite_SVI")
            else:
                # Only save the SVI_key_domain and composite_svi_z
                cols_to_save = ["SVI_key_domain", "composite_svi_z", "geometry"]

            # Filter out the roads because they do not have an SVI score
            filter_roads = exposure_data["primary_object_type"] != "roads"
            svi_exp_joined = gpd.sjoin(
                exposure_data.loc[filter_roads],
                svi.svi_data_shp[cols_to_save],
                how="left",
            )
            svi_exp_joined.drop(columns=["geometry"], inplace=True)
            svi_exp_joined = pd.DataFrame(svi_exp_joined)
            svi_exp_joined.rename(columns={"composite_svi_z": "SVI"}, inplace=True)
            del svi_exp_joined["index_right"]
            self.exposure.exposure_db = self.exposure.exposure_db.merge(
                svi_exp_joined[["object_id", "SVI_key_domain", "SVI"]],
                on="object_id",
                how="left",
            )
            # Define spatial join info
            file = "SVI/svi"
            self.set_geoms(gdf, file)
            attrs = {
                "name": "SVI",
                "file": f"exposure/{file}.gpkg",
                "field_name": "composite_svi_z",
            }
            if not self.spatial_joins["additional_attributes"]:
                self.spatial_joins["additional_attributes"] = []
            self.spatial_joins["additional_attributes"].append(attrs)

    def setup_equity_data(
        self,
        census_key: str,
        year_data: int = None,
    ):
        """Setup the download procedure for equity data similarly to the SVI setup

        Parameters
        ----------
        path_dataset : str
            The path to a predefined dataset
        census_key : str
            The user's unique Census key that they got from the census.gov website
            (https://api.census.gov/data/key_signup.html) to be able to download the
            Census data
        path : Union[str, Path]
            The path to the codebook excel
        """
        # First find the state(s) and county/counties where the exposure data is
        # located in
        us_states_counties = self.data_catalog.get_dataframe("us_states_counties")
        counties, states = locate_from_exposure(
            self.exposure.exposure_geoms[0]["geometry"]
        )
        states_dict = list_of_states()
        state_abbreviation = []
        for state in states:
            try:
                state_abbreviation.append(states_dict[state])
            except KeyError:
                self.logger.warning(f"State {state} not found.")

        county_numbers = get_us_county_numbers(counties, us_states_counties)

        # Create equity object
        save_folder = str(Path(self.root) / "exposure" / "equity")
        equity = EquityData(self.data_catalog, self.logger, save_folder)

        # Call functionalities of equity
        equity.set_up_census_key(census_key)
        equity.variables_to_download()
        equity.set_up_state_code(state_abbreviation)
        equity.download_census_data(year_data)
        equity.rename_census_data()
        equity.match_geo_ID()
        try:
            equity.download_shp_geom(year_data, county_numbers)
        except:
            self.logger.warning(
                "The census track shapefile could not be downloaded, potentially because the site is down. Aggregation areas and equity information will not be available in the FIAT model!"
            )
            return
        equity.merge_equity_data_shp()
        equity.clean()
        gdf = rename_geoid_short(equity.equity_data_shp)
        self.set_tables(df=gdf, name="equity_data")

        # Save the census block aggregation area data
        block_groups = equity.get_block_groups()

        # Update the aggregation label: Census Blockgroup
        del self.exposure.exposure_db["Aggregation Label: Census Blockgroup"]
        self.setup_aggregation_areas(
            aggregation_area_fn=block_groups,
            attribute_names="GEOID_short",
            label_names="Census Blockgroup",
            new_composite_area=False,
            file_names="block_groups",
        )

        # Update spatial join metadata for equity data connection
        ind = [
            i
            for i, name in enumerate(
                [aggr["name"] for aggr in self.spatial_joins["aggregation_areas"]]
            )
        ][0]
        attrs = {
            "census_data": "exposure/equity/equity_data.csv",  # TODO check how and where this is defined
            "percapitaincome_label": "PerCapitaIncomeBG",
            "totalpopulation_label": "TotalPopulationBG",
        }
        self.spatial_joins["aggregation_areas"][ind]["equity"] = attrs

    def setup_aggregation_areas(
        self,
        aggregation_area_fn: Union[
            List[str], List[Path], List[gpd.GeoDataFrame], str, Path, gpd.GeoDataFrame
        ] = "default",
        attribute_names: Union[List[str], str] = None,
        label_names: Union[List[str], str] = None,
        new_composite_area: bool = False,
        file_names: Union[List[str], str] = None,
        res_x: Union[int, float] = 1,
        res_y: Union[int, float] = 1,
    ):
        """_summary_

        Parameters
        ----------
        aggregation_area_fn : Union[List[str], List[Path], str, Path]
            Path(s) to the aggregation area(s).
        attribute_names : Union[List[str], str]
            Name of the attribute(s) to join.
        label_names : Union[List[str], str]
            The name that the new attribute will get in the exposure data.
        new_composite_area: bool
            Check whether exposure is a new composite area
        file_names : Union[List[str], str]
            The name of the spatial file(s) if saved in aggregation_areas/
            folder in the root directory (Default is None).
        res_x : Union[int, float]
            The x resolution of the default aggregation area grid if no aggregation is provided and
            aggregation_area_fn = "default",  default set to 1
        res_y : Union[int, float]
            The y resolution of the default aggregation area grid if no aggregation is provided and
            aggregation_area_fn = "default", default set to 1
        """
        # Assuming that all inputs are given in the same format check if one is not a list, and if not, transform everything to lists
        if aggregation_area_fn == "default":
            aggregation_area_fn, attribute_names, label_names, file_names = (
                self.create_default_aggregation(res_x, res_y)
            )
        else:
            if not isinstance(aggregation_area_fn, list):
                aggregation_area_fn = [aggregation_area_fn]
                attribute_names = [attribute_names]
                label_names = [label_names]
                if file_names:
                    file_names = [file_names]

        # Perform spatial join for each aggregation area provided
        # First get all exposure geometries
        exposure_gdf = self.exposure.get_full_gdf(self.exposure.exposure_db)
        self.exposure.exposure_db, _, areas_gdf = join_exposure_aggregation_areas(
            exposure_gdf,
            aggregation_area_fn,
            attribute_names,
            # Make sure that column name for aggregation areas includes the Aggregation Label part
            ["Aggregation Label: " + name for name in label_names],
            new_composite_area,
            keep_all=False,
        )

        if file_names:
            for area_gdf, file_name in zip(areas_gdf, file_names):
                self.set_geoms(area_gdf, f"aggregation_areas/{file_name}")

        # Save metadata on spatial joins
        if not self.spatial_joins["aggregation_areas"]:
            self.spatial_joins["aggregation_areas"] = []
        for label_name, file_name, attribute_name in zip(
            label_names, file_names, attribute_names
        ):
            attrs = {
                "name": label_name,
                "file": f"geoms/aggregation_areas/{file_name}.geojson",  # TODO Should we define this location somewhere globally?
                "field_name": attribute_name,
            }
            self.spatial_joins["aggregation_areas"].append(attrs)

        # Clean up temp aggregation file
        if attribute_names[0] == "default_aggregation":
            os.remove(aggregation_area_fn[0])

    def setup_additional_attributes(
        self,
        aggregation_area_fn: Union[
            List[str], List[Path], List[gpd.GeoDataFrame], str, Path, gpd.GeoDataFrame
        ],
        attribute_names: Union[List[str], str],
        label_names: Union[List[str], str],
        new_composite_area: bool = False,
    ):
        # Assuming that all inputs are given in the same format check if one is not a list, and if not, transform everything to lists
        if not isinstance(aggregation_area_fn, list):
            aggregation_area_fn = [aggregation_area_fn]
            attribute_names = [attribute_names]
            label_names = [label_names]

        # Perform spatial join for each aggregation area provided
        # First get all exposure geometries
        exposure_gdf = self.exposure.get_full_gdf(self.exposure.exposure_db)
        # Then perform spatial joins
        self.exposure.exposure_db, _, areas_gdf = join_exposure_aggregation_areas(
            exposure_gdf,
            aggregation_area_fn,
            attribute_names,
            label_names,
            new_composite_area,
            keep_all=False,
        )

        file_names = []
        for area_gdf, file_name in zip(areas_gdf, aggregation_area_fn):
            name = Path(file_name).stem
            self.set_geoms(area_gdf, f"additional_attributes/{name}")
            file_names.append(name)

        # Save metadata on spatial joins
        if not self.spatial_joins["additional_attributes"]:
            self.spatial_joins["additional_attributes"] = []

        # Check if additional attributes already exist
        add_attrs_existing = (
            [attr["name"] for attr in self.spatial_joins["additional_attributes"]]
            if self.spatial_joins["additional_attributes"] is not None
            else []
        )

        for label_name, file_name, attribute_name in zip(
            label_names, file_names, attribute_names
        ):
            attrs = {
                "name": label_name,
                "file": f"geoms/additional_attributes/{file_name}.geojson",  # TODO Should we define this location somewhere globally?
                "field_name": attribute_name,
            }
            # If not exist, add to spatial joins
            if label_name not in add_attrs_existing:
                self.spatial_joins["additional_attributes"].append(attrs)

    def setup_classification(
        self,
        source=Union[List[str], str, Path, List[Path]],
        attribute=Union[List[str], str],
        type_add=Union[List[str], str],
        old_values=Union[List[str], str],
        new_values=Union[List[str], str],
        damage_types=Union[List[str], str],
        remove_object_type=bool,
    ):
        """_summary_

         Parameters
         ----------
         source : Union[List[str], List[Path], str, Path]
             Path(s) to the user classification file.
         attribute : Union[List[str], str]
             Name of the column of the user data
        type_add : Union[List[str], str]
             Name of the attribute the user wants to update. Primary or Secondary
         old_values : Union[List[str], List[Path], str, Path]
             Name of the default (NSI) exposure classification
         new_values : Union[List[str], str]
             Name of the user exposure classification.
         exposure_linking_table : Union[List[str], str]
             Path(s) to the new exposure linking table(s).
         damage_types : Union[List[str], str]
             "structure"or/and "content"
         remove_object_type: bool
             True if Primary/secondary_object_type from old gdf should be removed in case the object type category changed completely eg. from RES to COM.
             E.g. primary_object_type holds old data (RES) and Secondary was updated with new data (COM2).
        """

        self.exposure.setup_occupancy_type(source, attribute, type_add)

        # Drop Object Type that has not been updated.

        if remove_object_type:
            if type_add == "primary_object_type":
                self.exposure.exposure_db.drop(
                    "secondary_object_type", axis=1, inplace=True
                )
            else:
                self.exposure.exposure_db.drop(
                    "primary_object_type", axis=1, inplace=True
                )
        linking_table_new = self.exposure.update_user_linking_table(
            old_values, new_values, self.vf_ids_and_linking_df
        )
        self.vf_ids_and_linking_df = linking_table_new
        self.exposure.link_exposure_vulnerability(
            linking_table_new, ["structure", "content"]
        )

    def setup_building_footprint(
        self,
        building_footprint_fn: Union[str, Path],
        attribute_name: str,
    ):
        """_summary_

        Parameters
        ----------
        exposure_gdf : gpd.GeoDataFrame
            Exposure data to join the building footprints to as "BF_FID".
        building_footprint_fn : Union[List[str], List[Path], str, Path]
            Path(s) to the building footprint.
        attribute_names : Union[List[str], str]
            Name of the building footprint ID to join.
        column_name: str = "BF_FID"
            Name of building footprint in new exposure output
        """

        exposure_gdf = self.exposure.get_full_gdf(self.exposure.exposure_db)
        self.exposure.exposure_db = join_exposure_building_footprints(
            exposure_gdf,
            building_footprint_fn,
            attribute_name,
        )

        # Set the building_footprint_fn property to save the building footprints
        self.building_footprint_fn = building_footprint_fn
        self.building_footprint = gpd.read_file(building_footprint_fn)

    def create_default_aggregation(
        self, res_x: Union[int, float] = None, res_y: Union[int, float] = None
    ):
        """
        Creates a default aggregation grid based on the specified region and resolution.

        This function generates a grid of polygon geometries over the given region with
        specified resolutions in the x and y directions. The grid is saved as a vector
        file, which can be used for aggregation purposes.

        Parameters
        ----------
        res_x : Union[int, float], optional
            The resolution in the x direction, by default 0.05.
        res_y : Union[int, float], optional
            The resolution in the y direction, by default 0.05.

        Returns
        -------
        List
            Lists of the file path to the saved aggregation grid vector file, the attribute name, label name and file name.
        """
        rotation = 0
        bounds = self.region.bounds
        width = int((bounds["maxx"] - bounds["minx"]) / res_x)
        height = int((bounds["maxy"] - bounds["miny"]) / res_y)

        length_x = bounds["maxx"] - bounds["minx"]
        length_y = bounds["maxy"] - bounds["miny"]

        # Adjust resolution or length to ensure alignment
        res_x = length_x / int(length_x / res_x)
        res_y = length_y / int(length_y / res_y)

        transform_affine = (
            res_x[0],
            rotation,
            bounds["minx"][0],
            rotation,
            -res_y[0],
            bounds["maxy"][0],
        )
        shape = (height, width)

        # aggregation_areas is the vector file of the grid.
        aggregation_areas = full_from_transform(transform_affine, shape)

        # Create vector file
        geometries = []
        for j, y in enumerate(aggregation_areas["y"]):
            for i, x in enumerate(aggregation_areas["x"]):
                cell_geom = box(
                    x.values - res_x / 2,
                    y.values - res_y / 2,
                    x.values + res_x / 2,
                    y.values + res_y / 2,
                )
                geometries.append(
                    {"geometry": cell_geom, "value": aggregation_areas[j, i].item()}
                )

        # Create a GeoDataFrame from the geometries
        crs = self.region.crs
        default_aggregation_gdf = gpd.GeoDataFrame(geometries, crs=crs)

        # Create Aggregation Label Value
        default_aggregation_gdf["value"] = [
        f"Aggr:{i}" for i in range(1, len(default_aggregation_gdf["geometry"]) + 1)]
        default_aggregation_gdf.rename(
            columns={"value": "default_aggregation"}, inplace=True
        )
        fd, default_aggregation_fn = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        default_aggregation_gdf.to_file(default_aggregation_fn, driver="GeoJSON")

        return (
            [default_aggregation_fn],
            ["default_aggregation"],
            ["default_aggregation"],
            ["default_aggregation_grid"],
        )

    # Update functions
    def update_all(self):
        self.logger.info("Updating all data objects...")
        self.update_tables()
        self.update_geoms()
        # self.update_maps()

    def update_tables(self):
        # Update the exposure data tables
        if self.exposure:
            self.set_tables(df=self.exposure.exposure_db, name="exposure")

        # Update the vulnerability data tables
        if self.vulnerability:
            self.set_tables(
                df=self.vulnerability.get_table(), name="vulnerability_curves"
            )

        if not self.vf_ids_and_linking_df.empty:
            # Add the vulnerability linking table to the tables object
            self.set_tables(
                df=self.vf_ids_and_linking_df, name="vulnerability_identifiers"
            )

    def update_geoms(self):
        # Update the exposure data geoms
        # This now doesnt do a whole lot and should be
        # handled somewhere else properly
        if not self.region.empty:
            self.set_geoms(self.region, "region")

    def update_maps(self):
        NotImplemented

    # I/O
    def read(self):
        """Method to read the complete model schematization and configuration from
        file."""
        self.logger.info(f"Reading model data from {self.root}")

        # Read the configuration file
        self.read_config(config_fn=str(Path(self.root).joinpath("settings.toml")))

        # Read spatial joins configurations
        sj_path = Path(self.root).joinpath("spatial_joins.toml")
        if sj_path.exists():
            sj = SpatialJoins.load_file(sj_path)
            self.spatial_joins = sj.attrs.model_dump()

        # TODO: determine if it is required to read the hazard files
        # hazard_maps = self.config["hazard"]["grid_file"]
        # self.read_grid(fn="hazard/{name}.nc")

        # Read the tables exposure and vulnerability
        self.read_tables()

        # Read the geometries
        self.read_geoms()

    def _configread(self, fn):
        """Parse Delft-FIAT configuration toml file to dict."""
        # Read the fiat configuration toml file.
        with open(fn, mode="rb") as fp:
            config = tomli.load(fp)
        return config

    def read_tables(self):
        """Read the model tables for vulnerability and exposure data."""
        if not self._write:
            self._tables = dict()  # start fresh in read-only mode

        self.logger.info("Reading model table files.")

        # Start with vulnerability table
        vulnerability_fn = Path(self.root) / self.get_config("vulnerability.file")
        if Path(vulnerability_fn).is_file():
            self.logger.debug(f"Reading vulnerability table {vulnerability_fn}")
            self.vulnerability = Vulnerability(fn=vulnerability_fn, logger=self.logger)
        else:
            self.logger.warning(f"File {vulnerability_fn} does not exist!")

        # Now with exposure
        exposure_fn = Path(self.root) / self.get_config("exposure.csv.file")
        if Path(exposure_fn).is_file():
            self.logger.debug(f"Reading exposure table {exposure_fn}")
            self.exposure = ExposureVector(
                crs=self.get_config("exposure.geom.crs"),
                logger=self.logger,
                unit=self.get_config("exposure.geom.unit"),
                damage_unit=self.get_config("exposure.damage_unit"),
                data_catalog=self.data_catalog,  # TODO: See if this works also when no data catalog is provided
            )
            self.exposure.read_table(exposure_fn)
        else:
            self.logger.warning(f"File {exposure_fn} does not exist!")

    def read_geoms(self):
        """Read the geometries for the exposure data."""
        if not self._write:
            self._geoms = dict()  # fresh start in read-only mode

        if self.exposure:
            self.logger.info("Reading exposure geometries.")
            exposure_files = [
                k for k in self.config["exposure"]["geom"].keys() if "file" in k
            ]
            exposure_fn = [
                Path(self.root) / self.get_config(f"exposure.geom.{f}")
                for f in exposure_files
            ]
            self.exposure.read_geoms(exposure_fn)

        fns = glob.glob(Path(self.root, "geoms", "*.geojson").as_posix())
        if self.spatial_joins["aggregation_areas"]:
            fns_aggregation = []
            for i in self.spatial_joins["aggregation_areas"]:
                fn_aggregation = i["file"]
                fn_aggregation = str(Path(self.root, fn_aggregation))
                fns_aggregation.append(fn_aggregation)
            fns.extend(fns_aggregation)
        if self.spatial_joins["additional_attributes"]:
            fns_additional_attributes = []
            for i in self.spatial_joins["additional_attributes"]:
                fn_additional_attributes = i["file"]
                fn_additional_attributes = str(
                    Path(self.root, fn_additional_attributes)
                )
                if "building_footprints" in fn_additional_attributes:
                    self.building_footprint = gpd.read_file(fn_additional_attributes)
                else:
                    fns_additional_attributes.append(fn_additional_attributes)
                fns.extend(fns_additional_attributes)

        if len(fns) >= 1:
            self.logger.info("Reading static geometries")
        for fn in fns:
            if "aggregation_areas" in fn:
                name = f"aggregation_areas/{Path(fn).stem}"
            elif "additional_attributes" in fn:
                name = f"additional_attributes/{Path(fn).stem}"
            else:
                name = Path(fn).stem
            self.set_geoms(gpd.read_file(fn), name=name)

    def write(self):
        """Method to write the complete model schematization and configuration to file."""
        self.update_all()
        self.logger.info(f"Writing model data to {self.root}")

        if self.maps:
            self.write_maps(fn="hazard/{name}.nc", gdal_compliant=True)
        if self.grid:
            self.write_grid(fn="hazard/risk_map.nc", gdal_compliant=True)
        # Use a custom write_geoms to handle the exposure geoms as an exception
        self.write_geoms()
        if self._tables:
            self.write_tables()
        if (
            self.spatial_joins["aggregation_areas"]
            or self.spatial_joins["additional_attributes"]
        ):
            self.write_spatial_joins()
        if self.building_footprint_fn:
            folder = Path(self.root).joinpath("geoms", "building_footprints")
            self.copy_datasets(self.building_footprint_fn, folder)
        if not self.building_footprint.empty:
            self.write_building_footprints()
        if self.config:  # try to read default if not yet set
            self.write_config()

    def copy_datasets(
        self, data: Union[list, str, Path], folder: Union[Path, str]
    ) -> None:
        """Copies datasets to another folder

        Parameters
        ----------
        data : Union[list, str, Path]
            _description_
        folder : Union[Path, str]
            _description_
        """
        # Create additional attributes folder in root
        if not os.path.exists(folder):
            os.makedirs(folder)

        if isinstance(data, list):
            for file in data:
                shutil.copy2(file, folder)
        elif isinstance(data, Path) or isinstance(data, str):
            shutil.copy2(data, folder)

    def write_spatial_joins(self) -> None:
        spatial_joins_conf = SpatialJoins.load_dict(self.spatial_joins)
        spatial_joins_conf.save(Path(self.root).joinpath("spatial_joins.toml"))

    def write_building_footprints(self) -> None:
        folder = Path(self.root).joinpath("geoms", "building_footprints")
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.building_footprint.to_file(
            Path(folder).joinpath("building_footprints.geojson")
        )

    def write_geoms(self):
        """_summary_."""
        if self.exposure and "exposure" in self._tables:
            fn = "exposure/{name}.gpkg"
            for i, (geom, name) in enumerate(
                zip(self.exposure.exposure_geoms, self.exposure.geom_names)
            ):
                _fn = os.path.join(self.root, fn.format(name=name))
                if not os.path.isdir(os.path.dirname(_fn)):
                    os.makedirs(os.path.dirname(_fn))

                # This whole ordeal is terrible,
                # but it needs a refactor that is too much to fix this properly
                self.set_config(
                    f"exposure.geom.file{str(i+1)}",
                    fn.format(name=name),
                )
                geom.to_file(_fn)
        if self.geoms:
            GridModel.write_geoms(self)

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
                kwargs = {"mode": "a", "index": False}

                # The vulnerability curves are written out differently because of
                # the metadata
                path = Path(self.root) / fn
                with open(path, "w", newline="") as f:
                    writer = csv.writer(f)

                    # First write the metadata
                    for metadata in self.vulnerability_metadata:
                        writer.writerow([metadata])
            # Exposure
            elif name == "exposure":
                # The default location and save settings of the exposure data
                fn = "exposure/exposure.csv"
                kwargs = {"index": False}
            elif name == "vulnerability_identifiers":
                # The default location and save settings of the vulnerability curves
                fn = "vulnerability/vulnerability_identifiers.csv"
                kwargs = {"index": False}
            elif name == "social_vulnerability_scores":
                fn = f"exposure/SVI/{name}.csv"
                kwargs = {"index": False}
            elif name == "equity_data":
                fn = f"exposure/equity/{name}.csv"
                kwargs = {"index": False}

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
        with open(fn, "wb") as f:
            tomli_w.dump(self.config, f)

    # FIAT specific attributes and methods
    @property
    def vulnerability_curves(self) -> pd.DataFrame:
        """Returns a dataframe with the damage functions."""
        if self.vulnerability:
            vf = self.vulnerability.get_table()
        else:
            vf = pd.DataFrame()
        return vf

    @property
    def vulnerability_metadata(self) -> List[str]:
        if self.vulnerability:
            vmeta = self.vulnerability.get_metadata()
        else:
            vmeta = list()
        return vmeta

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
