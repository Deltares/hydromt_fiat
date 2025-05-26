import geopandas as gpd
import pandas as pd
import pytest
from hydromt import DataCatalog


## Internal data structures
@pytest.fixture(scope="session")
def exposure_geom_cost_table(data_catalog: DataCatalog) -> pd.DataFrame:
    df = data_catalog.get_dataframe("damage_values")
    return df


@pytest.fixture(scope="session")
def exposure_geom_link_table(data_catalog: DataCatalog) -> pd.DataFrame:
    df = data_catalog.get_dataframe("buildings_link")
    return df


@pytest.fixture
def exposure_geom_raw_data(
    data_catalog: DataCatalog, build_region_small_gdf: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    gdf = data_catalog.get_geodataframe("buildings", geom=build_region_small_gdf)
    return gdf
