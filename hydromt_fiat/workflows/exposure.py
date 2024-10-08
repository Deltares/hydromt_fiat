from hydromt.data_catalog import DataCatalog
import geopandas as gpd
from logging import Logger
from typing import Optional


class Exposure:
    def __init__(
        self,
        data_catalog: DataCatalog,
        logger: Logger,
        region: Optional[gpd.GeoDataFrame] = None,
        crs: Optional[str] = None,
    ):
        self.data_catalog = data_catalog
        self.logger = logger
        self.region = region
        self.crs = crs
