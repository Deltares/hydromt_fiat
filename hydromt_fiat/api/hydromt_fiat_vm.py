from typing import Any, Union, List

import tomli_w
from hydromt import DataCatalog
from pathlib import Path

from hydromt_fiat.api.data_types import ConfigYaml
from hydromt_fiat.api.dbs_controller import LocalDatabase
from hydromt_fiat.api.exposure_vm import ExposureViewModel
from hydromt_fiat.api.model_vm import ModelViewModel
from hydromt_fiat.api.vulnerability_vm import VulnerabilityViewModel
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

    def clear_database(self):
        # TODO: delete database after hydromt_fiat has run
        ...

    def save_data_catalog(self):
        database_path = self.__class__.database.drive
        self.__class__.data_catalog.to_yml(database_path / "data_catalog.yml")

    def build_config_ini(self):
        config_ini = ConfigYaml(
            setup_global_settings=self.model_vm.global_settings_model,
            setup_output=self.model_vm.output_model,
            setup_vulnerability=self.vulnerability_vm.vulnerability_buildings_model,
            setup_road_vulnerability=self.vulnerability_vm.vulnerability_roads_model,
            setup_exposure_buildings=self.exposure_vm.exposure_buildings_model,
            setup_exposure_roads=self.exposure_vm.exposure_roads_model,
        )

        database_path = self.__class__.database.drive

        with open(database_path / "config.ini", "wb") as f:
            tomli_w.dump(config_ini.dict(exclude_none=True), f)

    def read(self):
        self.fiat_model.read()
        
    def run_hydromt_fiat(self):
        config_yaml = ConfigYaml(
            setup_global_settings=self.model_vm.global_settings_model,
            setup_output=self.model_vm.output_model,
            setup_vulnerability=self.vulnerability_vm.vulnerability_buildings_model,
            setup_road_vulnerability=self.vulnerability_vm.vulnerability_roads_model,
            setup_exposure_buildings=self.exposure_vm.exposure_buildings_model,
            setup_exposure_roads=self.exposure_vm.exposure_roads_model,
        )
        region = self.data_catalog.get_geodataframe("area_of_interest")
        self.fiat_model.build(region={"geom": region}, opt=config_yaml.dict())
        self.fiat_model.write()

    