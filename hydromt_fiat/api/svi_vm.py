from hydromt import DataCatalog

from hydromt_fiat.interface.database import IDatabase
from hydromt_fiat.workflows.social_vulnerability_index import list_of_states
import logging

from .data_types import (
    SocialVulnerabilityIndexSettings,
    EquityDataSettings,
)


class SviViewModel:
    def __init__(
        self, database: IDatabase, data_catalog: DataCatalog, logger: logging.Logger
    ):
        self.svi_model = None
        self.equity_model = None

        self.database: IDatabase = database
        self.data_catalog: DataCatalog = data_catalog
        self.logger: logging.Logger = logger

    @staticmethod
    def get_state_names():
        dict_states = list_of_states()
        return list(dict_states.keys())

    def set_svi_settings(self, census_key, year_data):
        self.svi_model = SocialVulnerabilityIndexSettings(
            census_key=census_key,
            codebook_fn="social_vulnerability",
            year_data=year_data,
        )

    def set_equity_settings(self, census_key, year_data):
        self.equity_model = EquityDataSettings(
            census_key=census_key,
            year_data=year_data,
        )
