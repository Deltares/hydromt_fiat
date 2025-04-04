from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import geopandas as gpd
import pandas as pd
import pytest
import xarray as xr
from hydromt import DataCatalog
from hydromt.model.root import ModelRoot
from pyproj.crs import CRS
from pytest_mock import MockerFixture
from shapely.geometry import box

from hydromt_fiat import FIATModel
from hydromt_fiat.data.fetch import fetch_data


## Cached and build data
@pytest.fixture(scope="session")
def build_data_cached() -> Path:  # The HydroMT-FIAT build data w/ catalog
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
def build_region_small_gdf(build_region_small) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(build_region_small)
    assert len(gdf) == 1
    return gdf


@pytest.fixture(scope="session")
def data_catalog(build_data_catalog) -> DataCatalog:
    dc = DataCatalog(build_data_catalog)
    assert "bag" in dc.sources
    return dc


@pytest.fixture(scope="session")
def osm_cached() -> Path:
    # Fetch the data
    p = fetch_data("osmnx")
    assert len(list(p.iterdir())) != 0
    return p


@pytest.fixture
def hazard_event_data(data_catalog, build_region_gdf) -> xr.DataArray:
    ds = data_catalog.get_rasterdataset("flood_event", geom=build_region_gdf)
    return ds


@pytest.fixture
def hazard_event_data_highres(data_catalog, build_region_gdf) -> xr.DataArray:
    ds = data_catalog.get_rasterdataset("flood_event_highres", geom=build_region_gdf)
    return ds


@pytest.fixture
def vulnerability_data(data_catalog) -> pd.DataFrame:
    df = data_catalog.get_dataframe("jrc_vulnerability_curves")
    assert len(df) != 0
    return df


@pytest.fixture
def vulnerability_linking(data_catalog) -> pd.DataFrame:
    df = data_catalog.get_dataframe("jrc_vulnerability_curves_linking")
    assert len(df) != 0
    return df


## Models and mocked objects
@pytest.fixture
def model(tmp_path, build_data_catalog) -> FIATModel:
    model = FIATModel(tmp_path, mode="w", data_libs=build_data_catalog)
    return model


@pytest.fixture
def mock_model(tmp_path, mocker: MockerFixture) -> MagicMock:
    model = mocker.create_autospec(FIATModel)
    model.root = mocker.create_autospec(ModelRoot(tmp_path), instance=True)
    model.root.path.return_value = tmp_path
    model.data_catalog = mocker.create_autospec(DataCatalog)
    # Set attributes for practical use
    type(model).crs = PropertyMock(side_effect=lambda: CRS.from_epsg(4326))
    type(model).root = PropertyMock(side_effect=lambda: ModelRoot(tmp_path))
    return model


## Extra data structures
@pytest.fixture
def box_geometry() -> gpd.GeoDataFrame:
    geom = gpd.GeoDataFrame(
        geometry=[box(4.355, 52.035, 4.365, 52.045)],
        crs=4326,
    )
    return geom
