from pathlib import Path
from unittest.mock import MagicMock

import geopandas as gpd
import pytest
from hydromt import DataCatalog
from hydromt.model.root import ModelRoot
from pytest_mock import MockerFixture

from hydromt_fiat import FIATModel
from hydromt_fiat.data.fetch import fetch_data


@pytest.fixture(scope="session")
def build_data_cached() -> Path:
    # Fetch the data
    p = fetch_data("build-data")
    assert Path(p, "buildings", "bag.fgb").is_file()
    return p


@pytest.fixture(scope="session")
def build_data_catalog(build_data_cached: Path) -> Path:
    p = Path(build_data_cached, "data_catalog.yml")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def build_region(build_data_cached) -> Path:
    p = Path(build_data_cached, "region.geojson")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def build_region_small(build_data_cached) -> Path:
    p = Path(build_data_cached, "region_small.geojson")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def build_region_gdf(build_region) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(build_region)
    assert len(gdf) == 1
    return gdf


@pytest.fixture(scope="session")
def build_region_small_gdf(build_region) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(build_region)
    assert len(gdf) == 1
    return gdf


@pytest.fixture(scope="session")
def data_catalog(build_data_catalog) -> DataCatalog:
    dc = DataCatalog(build_data_catalog)
    assert "bag" in dc.sources
    return dc


@pytest.fixture
def model(tmp_path, build_data_catalog) -> FIATModel:
    model = FIATModel(tmp_path, data_libs=build_data_catalog)
    return model


@pytest.fixture
def mock_model(tmp_path, mocker: MockerFixture) -> MagicMock:
    model = mocker.create_autospec(FIATModel)
    model.root = mocker.create_autospec(ModelRoot(tmp_path), instance=True)
    model.root.path.return_value = tmp_path
    model.data_catalog = mocker.create_autospec(DataCatalog)
    return model


@pytest.fixture(scope="session")
def osm_cached() -> Path:
    # Fetch the data
    p = fetch_data("osmnx")
    assert len(list(p.iterdir())) != 0
    return p
