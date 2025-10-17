from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
import xarray as xr
from hydromt import DataCatalog
from shapely.geometry import box

from hydromt_fiat import FIATModel
from hydromt_fiat.data import fetch_data


## Build data
@pytest.fixture(scope="session")
def build_data_path() -> Path:  # The HydroMT-FIAT build data w/ catalog
    # Fetch the data
    p = fetch_data("build-data")
    assert Path(p, "buildings", "buildings.fgb").is_file()
    return p


@pytest.fixture(scope="session")
def build_data_catalog_path(build_data_path: Path) -> Path:
    p = Path(build_data_path, "data_catalog.yml")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def build_region_path(build_data_path: Path) -> Path:
    p = Path(build_data_path, "region.geojson")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def build_region_small_path(build_data_path: Path) -> Path:
    p = Path(build_data_path, "region_small.geojson")
    assert p.is_file()
    return p


@pytest.fixture
def build_region(build_region_path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(build_region_path)
    assert len(gdf) == 1
    return gdf


@pytest.fixture
def build_region_small(build_region_small_path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(build_region_small_path)
    assert len(gdf) == 1
    return gdf


@pytest.fixture(scope="session")
def build_data_catalog(build_data_catalog_path: Path) -> DataCatalog:
    dc = DataCatalog(build_data_catalog_path)
    assert "buildings" in dc.sources
    return dc


## Model data
@pytest.fixture(scope="session")
def model_data_path() -> Path:
    # Fetch the data
    p = fetch_data("fiat-model")
    assert len(list(p.iterdir())) != 0
    return p


@pytest.fixture
def exposure_vector(model_data_path: Path) -> gpd.GeoDataFrame:
    p = Path(model_data_path, "exposure", "buildings.fgb")
    assert p.is_file()
    gdf = gpd.read_file(p)
    assert len(gdf) != 0
    return gdf


@pytest.fixture
def exposure_grid(model_data_path: Path) -> xr.Dataset:
    p = Path(model_data_path, "exposure", "spatial.nc")
    assert p.is_file()
    ds = xr.open_dataset(p)
    assert len(ds.data_vars) != 0
    return ds


@pytest.fixture
def hazard(model_data_path: Path) -> xr.Dataset:
    p = Path(
        model_data_path,
        "hazard.nc",
    )
    assert p.is_file()
    ds = xr.open_dataset(p)
    assert len(ds.data_vars) != 0
    return ds


@pytest.fixture(scope="session")
def vulnerability_curves(model_data_path: Path) -> pd.DataFrame:
    p = Path(model_data_path, "vulnerability", "curves.csv")
    assert p.is_file()
    df = pd.read_csv(p)
    assert len(df) != 0
    return df


@pytest.fixture(scope="session")
def vulnerability_identifiers(model_data_path: Path) -> pd.DataFrame:
    p = Path(model_data_path, "vulnerability", "curves_id.csv")
    assert p.is_file()
    df = pd.read_csv(p)
    assert len(df) != 0
    return df


## Model data (clipped)
@pytest.fixture(scope="session")
def model_data_clipped_path() -> Path:
    # Fetch the data
    p = fetch_data("fiat-model-c")
    assert len(list(p.iterdir())) != 0
    return p


@pytest.fixture
def exposure_vector_clipped(model_data_clipped_path: Path) -> gpd.GeoDataFrame:
    p = Path(model_data_clipped_path, "exposure", "buildings.fgb")
    assert p.is_file()
    gdf = gpd.read_file(p)
    assert len(gdf) != 0
    return gdf


@pytest.fixture
def exposure_vector_clipped_for_damamge(
    exposure_vector_clipped: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    exposure_vector_clipped.drop(
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
    return exposure_vector_clipped


@pytest.fixture
def exposure_grid_clipped(model_data_clipped_path: Path) -> xr.Dataset:
    p = Path(model_data_clipped_path, "exposure", "spatial.nc")
    assert p.is_file()
    ds = xr.open_dataset(p)
    assert len(ds.data_vars) != 0
    return ds


@pytest.fixture
def hazard_clipped(model_data_clipped_path: Path) -> xr.Dataset:
    p = Path(
        model_data_clipped_path,
        "hazard.nc",
    )
    assert p.is_file()
    ds = xr.open_dataset(p)
    assert len(ds.data_vars) != 0
    return ds


## OSM data
@pytest.fixture(scope="session")
def osm_data_path() -> Path:
    # Fetch the data
    p = fetch_data("osmnx")
    assert len(list(p.iterdir())) != 0
    return p


## Models and mocked objects
@pytest.fixture
def model(tmp_path: Path, build_data_catalog_path: Path) -> FIATModel:
    model = FIATModel(tmp_path, mode="w", data_libs=build_data_catalog_path)
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
