from hydromt import DataCatalog

from hydromt_fiat.interface.database import IDatabase
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

    def set_svi_settings(self, census_key, state_abbreviation, year_data, county):
        self.svi_model = SocialVulnerabilityIndexSettings(
            census_key = census_key,
            codebook_fn = "social_vulnerability",
            state_abbreviation = state_abbreviation,
            year_data = year_data,
            county = county,
        )
    
    def set_equity_settings(self, census_key, state_abbreviation, year_data, county):
        self.equity_model = EquityDataSettings(
            census_key = census_key,
            state_abbreviation = state_abbreviation,
            year_data = year_data,
            county = county,
        )
