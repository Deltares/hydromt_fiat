from hydromt.data_catalog import DataCatalog
import geopandas as gpd


class Exposure:
    def __init__(
        self, data_catalog: DataCatalog, config: dict, region: gpd.GeoDataFrame = None
    ):
        self.data_catalog = data_catalog
        self.config = config
        self.region = region
