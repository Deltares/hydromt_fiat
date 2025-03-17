from pathlib import Path

import pytest
from hydromt import DataCatalog

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
def data_catalog(build_data_catalog):
    dc = DataCatalog(build_data_catalog)
    assert "bag" in dc.sources
    return dc
