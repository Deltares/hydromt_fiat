from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
import xarray as xr
from hydromt import DataCatalog
from shapely.geometry import box

from hydromt_fiat import FIATModel
from hydromt_fiat.data import fetch_data


## Cached build data
@pytest.fixture(scope="session")
def build_data_cached() -> Path:  # The HydroMT-FIAT build data w/ catalog
    # Fetch the data
    p = fetch_data("build-data")
    assert Path(p, "buildings", "buildings.fgb").is_file()
    return p


@pytest.fixture(scope="session")
def build_data_catalog(build_data_cached: Path) -> Path:
    p = Path(build_data_cached, "data_catalog.yml")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def build_region(build_data_cached: Path) -> Path:
    p = Path(build_data_cached, "region.geojson")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def build_region_small(build_data_cached: Path) -> Path:
    p = Path(build_data_cached, "region_small.geojson")
    assert p.is_file()
    return p


@pytest.fixture
def build_region_gdf(build_region: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(build_region)
    assert len(gdf) == 1
    return gdf


@pytest.fixture
def build_region_small_gdf(build_region_small: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(build_region_small)
    assert len(gdf) == 1
    return gdf


@pytest.fixture(scope="session")
def data_catalog(build_data_catalog: Path) -> DataCatalog:
    dc = DataCatalog(build_data_catalog)
    assert "buildings" in dc.sources
    return dc


## Cached model data
@pytest.fixture(scope="session")
def model_cached() -> Path:
    # Fetch the data
    p = fetch_data("fiat-model")
    assert len(list(p.iterdir())) != 0
    return p


@pytest.fixture
def exposure_geom_data(model_cached: Path) -> gpd.GeoDataFrame:
    p = Path(model_cached, "exposure", "buildings.fgb")
    assert p.is_file()
    gdf = gpd.read_file(p)
    assert len(gdf) != 0
    return gdf


@pytest.fixture
def exposure_geom_data_damage(
    exposure_geom_data: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    exposure_geom_data.drop(
        [
            "cost_type",
            "max_damage_structure",
            "max_damage_content",
            "ground_flht",
            "ground_elevtn",
            "extract_method",
        ],
        axis=1,
        inplace=True,
    )
    return exposure_geom_data


@pytest.fixture
def exposure_grid_data(model_cached: Path) -> xr.Dataset:
    p = Path(model_cached, "exposure", "spatial.nc")
    assert p.is_file()
    ds = xr.open_dataset(p)
    assert len(ds.data_vars) != 0
    return ds


@pytest.fixture
def hazard_data(model_cached: Path) -> xr.Dataset:
    p = Path(
        model_cached,
        "hazard.nc",
    )
    assert p.is_file()
    ds = xr.open_dataset(p)
    assert len(ds.data_vars) != 0
    return ds


@pytest.fixture(scope="session")
def vulnerability_curves(model_cached: Path) -> pd.DataFrame:
    p = Path(model_cached, "vulnerability", "curves.csv")
    assert p.is_file()
    df = pd.read_csv(p)
    assert len(df) != 0
    return df


@pytest.fixture(scope="session")
def vulnerability_identifiers(model_cached: Path) -> pd.DataFrame:
    p = Path(model_cached, "vulnerability", "curves_id.csv")
    assert p.is_file()
    df = pd.read_csv(p)
    assert len(df) != 0
    return df


## Cached OSM data
@pytest.fixture(scope="session")
def osm_cached() -> Path:
    # Fetch the data
    p = fetch_data("osmnx")
    assert len(list(p.iterdir())) != 0
    return p


## Models and mocked objects
@pytest.fixture
def model(tmp_path: Path, build_data_catalog: Path) -> FIATModel:
    model = FIATModel(tmp_path, mode="w", data_libs=build_data_catalog)
    return model


@pytest.fixture
def model_with_region(
    model: FIATModel,
    build_region_small: Path,
) -> FIATModel:
    model.setup_region(build_region_small)
    return model


## Extra data structures
@pytest.fixture
def box_geometry() -> gpd.GeoDataFrame:
    geom = gpd.GeoDataFrame(
        geometry=[box(4.355, 52.035, 4.365, 52.045)],
        crs=4326,
    )
    return geom
