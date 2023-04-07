from hydromt.data_catalog import DataCatalog
import geopandas as gpd


class Exposure:
    def __init__(
        self,
        data_catalog: DataCatalog,
        region: gpd.GeoDataFrame = None,
        crs: str = None,
    ):
        self.data_catalog = data_catalog
        self.region = region
        self.crs = crs
