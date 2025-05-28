from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
import xarray as xr
from hydromt import DataCatalog


## Data from the data catalog
@pytest.fixture
def buildings_data(
    data_catalog: DataCatalog, build_region_small_gdf: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    gdf = data_catalog.get_geodataframe("buildings", geom=build_region_small_gdf)
    return gdf


@pytest.fixture(scope="session")
def buildings_link_table(data_catalog: DataCatalog) -> pd.DataFrame:
    df = data_catalog.get_dataframe("buildings_link")
    return df


@pytest.fixture(scope="session")
def exposure_cost_table(data_catalog: DataCatalog) -> pd.DataFrame:
    df = data_catalog.get_dataframe("damage_values")
    return df


@pytest.fixture
def hazard_event_data(
    data_catalog: DataCatalog, build_region_gdf: gpd.GeoDataFrame
) -> xr.DataArray:
    ds = data_catalog.get_rasterdataset("flood_event", geom=build_region_gdf)
    return ds


@pytest.fixture
def hazard_event_data_highres(
    data_catalog: DataCatalog,
    build_region_gdf: gpd.GeoDataFrame,
) -> xr.DataArray:
    ds = data_catalog.get_rasterdataset("flood_event_highres", geom=build_region_gdf)
    return ds


@pytest.fixture
def vulnerability_data(data_catalog: DataCatalog) -> pd.DataFrame:
    df = data_catalog.get_dataframe("vulnerability_curves")
    assert len(df) != 0
    return df


@pytest.fixture
def vulnerability_linking(data_catalog: DataCatalog) -> pd.DataFrame:
    df = data_catalog.get_dataframe("vulnerability_curves_linking")
    assert len(df) != 0
    return df


@pytest.fixture
def vulnerability_linking_alt(data_catalog: DataCatalog) -> pd.DataFrame:
    df = data_catalog.get_dataframe("vulnerability_curves_linking_alt")
    assert len(df) != 0
    return df


## Data from a prebuild model
@pytest.fixture
def exposure_geom_data_alt(model_cached: Path) -> gpd.GeoDataFrame:
    p = Path(model_cached, "exposure", "buildings_alt.fgb")
    assert p.is_file()
    gdf = gpd.read_file(p)
    assert len(gdf) != 0
    return gdf


@pytest.fixture(scope="session")
def vulnerability_curves_alt(model_cached: Path) -> pd.DataFrame:
    p = Path(model_cached, "vulnerability", "vulnerability_curves_alt.csv")
    assert p.is_file()
    df = pd.read_csv(p)
    assert len(df) != 0
    return df


@pytest.fixture(scope="session")
def vulnerability_identifiers_alt(model_cached: Path) -> pd.DataFrame:
    p = Path(model_cached, "vulnerability", "vulnerability_identifiers_alt.csv")
    assert p.is_file()
    df = pd.read_csv(p)
    assert len(df) != 0
    return df
