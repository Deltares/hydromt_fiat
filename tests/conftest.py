from pathlib import Path

import geopandas as gpd
import pytest

from hydromt_fiat.data.fetch import fetch_data


@pytest.fixture(scope="session")
def build_data_cached():
    # Fetch the data
    p = fetch_data("build-data")
    assert Path(p, "buildings", "bag.fgb").is_file()
    return p


@pytest.fixture(scope="session")
def build_data_catalog(build_data_cached: Path):
    p = Path(build_data_cached, "data_catalog.yml")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def build_region(build_data_cached):
    p = Path(build_data_cached, "region.geojson")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def build_region_gdf(build_region):
    return gpd.read_file(build_region)
