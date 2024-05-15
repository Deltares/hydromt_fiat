from typing import Any, Union, List
import geopandas as gpd

import tomli_w
from hydromt import DataCatalog
from pathlib import Path

from hydromt_fiat.api.data_types import ConfigYaml
from hydromt_fiat.api.dbs_controller import LocalDatabase
from hydromt_fiat.api.exposure_vm import ExposureViewModel
from hydromt_fiat.api.model_vm import ModelViewModel
from hydromt_fiat.api.vulnerability_vm import VulnerabilityViewModel
from hydromt_fiat.api.svi_vm import SviViewModel
from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog


class HydroMtViewModel:
    data_catalog: DataCatalog
    database: LocalDatabase

    def __init__(
        self,
        database_path: str,
        catalog_path: Union[List, str],
        hydromt_fiat_path: str,
    ):
        database_path = Path(database_path)

        HydroMtViewModel.database = LocalDatabase.create_database(database_path)
        HydroMtViewModel.data_catalog = DataCatalog(catalog_path)

        logger = setuplog("hydromt_fiat", log_level=10)
        # NOTE: with w+ hydromt_fiat allows to create a model in a folder that
        # already contains data, with w this is not allowed (I would say the
        # latter is preferred, but w is handy for testing)
        self.fiat_model = FiatModel(
            data_libs=catalog_path,
            root=hydromt_fiat_path,
            mode="w+",
            logger=logger,
        )

        self.model_vm = ModelViewModel()
        self.exposure_vm = ExposureViewModel(
            HydroMtViewModel.database, HydroMtViewModel.data_catalog, logger
        )
        self.vulnerability_vm = VulnerabilityViewModel(
            HydroMtViewModel.database, HydroMtViewModel.data_catalog, logger
        )
        self.svi_vm = SviViewModel(
            HydroMtViewModel.database, HydroMtViewModel.data_catalog, logger
        )

    def clear_database(self):
        # TODO: delete database after hydromt_fiat has run
        ...

    def save_data_catalog(self):
        database_path = self.__class__.database.drive
        self.__class__.data_catalog.to_yml(database_path / "data_catalog.yml")

    def build_config_yaml(self):
        config_yaml = ConfigYaml(
            setup_global_settings=self.model_vm.global_settings_model,
            setup_output=self.model_vm.output_model,
        )

        # Make sure the order of the configurations is correct
        if self.vulnerability_vm.vulnerability_buildings_model:
            config_yaml.setup_vulnerability = (
                self.vulnerability_vm.vulnerability_buildings_model
            )

        if self.exposure_vm.exposure_buildings_model:
            config_yaml.setup_exposure_buildings = (
                self.exposure_vm.exposure_buildings_model
            )

        if self.exposure_vm.aggregation_areas_model:
            config_yaml.setup_aggregation_areas = (
                self.exposure_vm.aggregation_areas_model
            )
        
        if self.exposure_vm.classification_model:
            config_yaml.setup_classification = (
                self.exposure_vm.classification_model
            )

        if self.exposure_vm.exposure_damages_model:
            config_yaml.update_max_potential_damage = (
                self.exposure_vm.exposure_damages_model
            )

        if self.exposure_vm.exposure_ground_floor_height_model:
            config_yaml.update_ground_floor_height = (
                self.exposure_vm.exposure_ground_floor_height_model
            )
        
        if self.exposure_vm.exposure_ground_elevation_model:
            config_yaml.update_ground_elevation = (
                self.exposure_vm.exposure_ground_elevation_model
            )

        if self.exposure_vm.exposure_roads_model:
            config_yaml.setup_exposure_roads = self.exposure_vm.exposure_roads_model

        if self.vulnerability_vm.vulnerability_roads_model:
            config_yaml.setup_road_vulnerability = (
                self.vulnerability_vm.vulnerability_roads_model
            )

        if self.svi_vm.svi_model:
            config_yaml.setup_social_vulnerability_index = self.svi_vm.svi_model

        if self.svi_vm.equity_model:
            config_yaml.setup_equity_data = self.svi_vm.equity_model

        database_path = self.__class__.database.drive

        with open(database_path / "config.yaml", "wb") as f:
            tomli_w.dump(config_yaml.dict(exclude_none=True), f)

        return config_yaml

    def read(self):
        self.fiat_model.read()

    def run_hydromt_fiat(self):
        self.save_data_catalog()
        config_yaml = self.build_config_yaml()

        # TODO: add some more checks to see if HydroMT-FIAT can be run
        if ("setup_vulnerability" not in config_yaml.dict()) and (
            "setup_exposure_buildings" in config_yaml.dict()
        ):
            raise Exception(
                "Please set up the vulnerability data before creating a Delft-FIAT model."
            )
        elif "setup_exposure_buildings" not in config_yaml.dict():
            raise Exception(
                "Please set up the exposure and vulnerability data before creating a Delft-FIAT model."
            )

        region = self.data_catalog.get_geodataframe("area_of_interest")
        self.fiat_model.build(region={"geom": region}, opt=config_yaml.dict())

        # Update exposure dataframe
        buildings_gdf, roads_gdf = self.update_exposure_db(config_yaml)
        return buildings_gdf, roads_gdf

    def update_model(self, parameter):

        #Update config yaml
        self.save_data_catalog()
        config_yaml = self.build_config_yaml()

        # Update parameter with user-input
        if isinstance(parameter,list):
            for item in parameter:
                if "Finished Floor Height" in item:
                    self.new_ground_floor_height(config_yaml)
                elif "Additional Attributes" in item :
                    self.new_additional_attributes(config_yaml)
                elif"Ground Elevation" in item:
                    self.new_ground_elevation(config_yaml)
                elif "Max Potential Damages" in item :
                    self.new_max_potential_damages(config_yaml)
        elif isinstance(parameter, str):
            parameter = [parameter]
            for item in parameter:
                if "Finished Floor Height" in item:
                    self.new_ground_floor_height(config_yaml)
                elif "Additional Attributes" in item :
                    self.new_additional_attributes(config_yaml)
                elif"Ground Elevation" in item:
                    self.new_ground_elevation(config_yaml)
                elif "Max Potential Damages" in item :
                    self.new_max_potential_damages(config_yaml)
       
        # Write model
        self.fiat_model.write()

        buildings_gdf, roads_gdf = self.update_exposure_db(config_yaml)
        return buildings_gdf, roads_gdf
        
    # Update exposure dataframe
    def update_exposure_db(self, config_yaml):
        exposure_db = self.fiat_model.exposure.exposure_db

        # create function out of it and use "Primary/Secondary" as input 
        if (
            "setup_exposure_buildings" in config_yaml.dict()
            and "setup_exposure_roads" not in config_yaml.dict()
        ):
            # Only buildings are set up
            buildings_gdf = self.fiat_model.exposure.get_full_gdf(exposure_db)
            return buildings_gdf, None
        elif (
            "setup_exposure_buildings" in config_yaml.dict()
            and "setup_exposure_roads" in config_yaml.dict()
        ):
            # Buildings and roads are set up
            full_gdf = self.fiat_model.exposure.get_full_gdf(exposure_db)
            buildings_gdf = full_gdf.loc[full_gdf["Primary Object Type"] != "roads"]
            if "SVI" in full_gdf.columns and "SVI_key_domain" in full_gdf.columns:
                roads_gdf = full_gdf.drop(["SVI", "SVI_key_domain"], axis=1).loc[
                full_gdf["Primary Object Type"] == "roads"]
            else:
                roads_gdf = full_gdf.loc[
                full_gdf["Primary Object Type"] == "roads"]
            
            return buildings_gdf, roads_gdf
        elif (
            "setup_exposure_buildings" not in config_yaml.dict()
            and "setup_exposure_roads" in config_yaml.dict()
        ):
            # Only roads are set up
            roads_gdf = self.fiat_model.exposure.get_full_gdf(exposure_db).drop(
                ["SVI", "SVI_key_domain"], axis=1
            )
            return None, roads_gdf

    def new_ground_floor_height(self, config_yaml):
        source = config_yaml.model_extra["update_ground_floor_height"].source
        attribute_name = config_yaml.model_extra["update_ground_floor_height"].attribute_name
        gfh_method = config_yaml.model_extra["update_ground_floor_height"].gfh_method
        max_dist = config_yaml.model_extra["update_ground_floor_height"].max_dist
        self.fiat_model.exposure.setup_ground_floor_height(source, attribute_name, gfh_method, max_dist)
    
    def new_additional_attributes(self, config_yaml):
        aggregation_area_fn = config_yaml.model_extra["setup_aggregation_areas"].aggregation_area_fn
        attribute_names = config_yaml.model_extra["setup_aggregation_areas"].attribute_names
        label_names = config_yaml.model_extra["setup_aggregation_areas"].label_names
        self.fiat_model.setup_aggregation_areas(aggregation_area_fn, attribute_names, label_names)

    def new_ground_elevation(self, config_yaml):
        source = config_yaml.model_extra["update_ground_elevation"].source
        unit = config_yaml.model_extra["update_ground_elevation"].unit
        self.fiat_model.exposure.setup_ground_elevation(source, unit)

    def new_max_potential_damages(self, config_yaml):
        source = config_yaml.model_extra["update_max_potential_damage"].source
        attribute_name = config_yaml.model_extra["update_max_potential_damage"].attribute_name
        method_damages = config_yaml.model_extra["update_max_potential_damage"].method_damages
        max_dist = config_yaml.model_extra["update_max_potential_damage"].max_dist
        damage_types = config_yaml.model_extra["update_max_potential_damage"].damage_types
        self.fiat_model.update_max_potential_damage(source, damage_types, attribute_name = attribute_name,method_damages = method_damages , max_dist = max_dist )