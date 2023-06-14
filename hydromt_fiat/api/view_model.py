from pathlib import Path
from typing import Any

from hydromt import DataCatalog

from hydromt_fiat.api.dbs_controller import LocalDatabase
from hydromt_fiat.api.exposure import ExposureViewModel
from hydromt_fiat.api.hazard import HazardViewModel
from hydromt_fiat.api.vulnerability import VulnerabilityViewModel
from hydromt_fiat.interface.database import IDatabase


class Singleton(object):
    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls)
        return cls._instance


class HydroMtViewModel(Singleton):
    data_catalog: DataCatalog
    database: IDatabase

    def __init__(self, database_path: Path, catalog_path: str):
        self.exposure_vm = ExposureViewModel()
        self.vulnerability_vm = VulnerabilityViewModel()
        self.hazard_vm = HazardViewModel()

        HydroMtViewModel.data_catalog = DataCatalog(catalog_path)
        HydroMtViewModel.database = LocalDatabase.create_database(database_path)

    def run_hydromt_fiat(self):
        # create ini file
        ...
