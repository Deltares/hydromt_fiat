from hydromt.data_catalog import DataCatalog
import geopandas as gpd
from logging import Logger


class Exposure:
    def __init__(
        self,
        data_catalog: DataCatalog,
        logger: Logger,
        region: gpd.GeoDataFrame = None,
        crs: str = None,
    ):
        self.data_catalog = data_catalog
        self.logger = logger
        self.region = region
        self.crs = crs
