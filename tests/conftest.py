import math
import re
import shutil
from functools import wraps
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
import xarray as xr
from hydromt import DataCatalog
from hydromt.gis import full_from_transform
from hydromt.readers import open_nc
from requests.exceptions import ConnectionError, RequestException
from shapely.geometry import box
from urllib3.exceptions import HTTPError

from hydromt_fiat import FIATModel
from hydromt_fiat.data import fetch_data
from hydromt_fiat.readers import read_config, read_grid
from hydromt_fiat.utils import CURVE, SQUARE__ID
from hydromt_fiat.writers import write_config

CACHE_DIR = Path(Path(__file__).parents[1], ".cache")


def check_connection(error: bool = True):
    def outer(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            try:
                r = fn(*args, **kwargs)
            except (HTTPError, OSError, RequestException) as e:
                if not error:
                    pytest.skip(reason="Connection timeout..")
                    return
                raise ConnectionError(
                    "Failed to download test data, check your connection"
                ) from e
            else:
                return r

        return inner

    return outer


def update_model_settings(path: Path) -> Path:
    # Add the variables settings to the (older) settings files of the downloaded data
    hazard = read_grid(Path(path, "hazard.nc"))
    exposure = read_grid(Path(path, "exposure", "spatial.nc"))
    curves = read_grid(Path(path, "curves.nc"))
    hazard_vars = [
        {"name": str(var), "type": "water_depth"} for var in hazard.data_vars
    ]
    vulnerability_vars = [
        {
            "name": str(var),
            "method": "flood.depth",
            "types": {str(dim): "water_depth" for dim in curves[var].dims[:1]},
        }
        for var in curves.data_vars
    ]
    exposure_vars = []
    for var in exposure.data_vars:
        attrs = exposure[var].attrs
        # Layers in the grid are either default, categorized or values
        if attrs.get("type") == "default":
            entry = {"fn_curve": attrs["fn_curve"], "vulnerability": "default"}
        elif attrs.get("type") == "categorized":
            entry = {"values": [f"{var}_structure", f"{var}_content"]}
        else:
            entry = {"vulnerability": "default"}
        exposure_vars.append({"name": str(var), "type": attrs.get("type", "values")})
        exposure_vars[-1].update(entry)

    # Update the settings files
    for fname in ["settings_geom.toml", "settings_grid.toml"]:
        config = read_config(Path(path, fname))
        config.pop("method", None)
        config["vulnerability"]["variables"] = vulnerability_vars
        config["hazard"]["variables"] = hazard_vars
        if isinstance(config["exposure"], list):
            for item in config["exposure"]:
                item["vulnerability"] = "default"
        else:
            config["exposure"]["variables"] = exposure_vars
        write_config(config, Path(path, fname))
    return path


def copy_model_data(name: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Copy the data, so the downloaded (cached) data is left untouched
    p = fetch_data(name, cache_dir=CACHE_DIR)
    assert len(list(p.iterdir())) != 0
    dst = Path(tmp_path_factory.mktemp(name), name)
    shutil.copytree(p, dst)
    return update_model_settings(dst)


## Build data
@pytest.fixture(scope="session")
@check_connection()
def build_data_path() -> Path:  # The HydroMT-FIAT build data w/ catalog
    # Fetch the data
    p = fetch_data("test-build-data", cache_dir=CACHE_DIR)
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


## Global data
@pytest.fixture(scope="session")
@check_connection()
def global_data_path() -> Path:  # The HydroMT-FIAT build data w/ catalog
    # Fetch the data
    p = fetch_data("global-data", cache_dir=CACHE_DIR)
    assert Path(p, "exposure", "jrc_damage_values.csv").is_file()
    return p


@pytest.fixture(scope="session")
def global_data_catalog_path(global_data_path: Path) -> Path:
    p = Path(global_data_path, "data_catalog.yml")
    assert p.is_file()
    return p


@pytest.fixture(scope="session")
def global_data_catalog(global_data_catalog_path: Path) -> DataCatalog:
    dc = DataCatalog(global_data_catalog_path)
    assert "osm_buildings" in dc.sources
    return dc


## Model data
@pytest.fixture(scope="session")
@check_connection()
def model_data_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Fetch the data
    return copy_model_data("fiat-model", tmp_path_factory)


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
    ds = open_nc(p, mask_and_scale=False)
    assert len(ds.data_vars) != 0
    return ds


@pytest.fixture
def hazard(model_data_path: Path) -> xr.Dataset:
    p = Path(
        model_data_path,
        "hazard.nc",
    )
    assert p.is_file()
    ds = open_nc(p, mask_and_scale=False)
    assert len(ds.data_vars) != 0
    return ds


@pytest.fixture
def vulnerability_curves(model_data_path: Path) -> xr.Dataset:
    p = Path(model_data_path, "curves.nc")
    assert p.is_file()
    ds = open_nc(p)
    assert len(ds) != 0
    return ds


@pytest.fixture
def vulnerability_curves_df(vulnerability_curves: xr.Dataset) -> pd.DataFrame:
    df = vulnerability_curves.default.to_pandas()
    df.index.name = "depth"
    df.columns.name = None
    return df.reset_index()


@pytest.fixture(scope="session")
def vulnerability_identifiers(model_data_path: Path) -> xr.Dataset:
    p = Path(model_data_path, "curves_id.nc")
    assert p.is_file()
    ds = open_nc(p)
    assert len(ds) != 0
    return ds


@pytest.fixture(scope="session")
def vulnerability_identifiers_df(
    vulnerability_identifiers: xr.Dataset,
) -> pd.DataFrame:
    ds = vulnerability_identifiers
    # Translate to pandas dataframe and reset the multiindex
    df = ds["curve_default"].to_dataframe().reset_index()

    # Substitute the column names by generic ones
    pattern = re.compile("(.*)_default")
    default_col_names = [pattern.findall(item)[0] for item in df.columns]
    df = df.rename(dict(zip(df.columns, default_col_names)), axis=1)
    df = df.dropna(subset=CURVE, how="any")
    return df


## Model data (clipped)
@pytest.fixture(scope="session")
@check_connection()
def model_data_clipped_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Fetch the data
    return copy_model_data("fiat-model-c", tmp_path_factory)


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
    exposure_vector_clipped = exposure_vector_clipped.drop(
        [
            "cost_type",
            "max_damage_structure",
            "max_damage_content",
            "elevation",
        ],
        axis=1,
    )
    return exposure_vector_clipped


@pytest.fixture
def exposure_vector_clipped_for_link(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    exposure_vector_clipped_for_damamge = exposure_vector_clipped_for_damamge.drop(
        [
            "fn_damage_structure",
            "fn_damage_content",
        ],
        axis=1,
    )
    return exposure_vector_clipped_for_damamge


@pytest.fixture
def exposure_vector_clipped_split_path(
    tmp_path: Path,
    exposure_vector_clipped: gpd.GeoDataFrame,
) -> Path:
    p = Path(tmp_path, "foo.fgb")
    # Seperate the geometry data
    geom = exposure_vector_clipped.loc[:, ["object_id", "geometry"]]
    geom.to_file(p)
    assert p.is_file()
    # Separate the tabular data
    cols = exposure_vector_clipped.columns.values.tolist()
    cols.remove("geometry")
    data = exposure_vector_clipped.loc[:, cols]
    data.to_csv(p.with_suffix(".csv"), index=False)
    assert p.with_suffix(".csv").is_file()
    return p


@pytest.fixture
def exposure_grid_clipped(model_data_clipped_path: Path) -> xr.Dataset:
    p = Path(model_data_clipped_path, "exposure", "spatial.nc")
    assert p.is_file()
    ds = open_nc(p, mask_and_scale=False)
    assert len(ds.data_vars) != 0
    return ds


@pytest.fixture
def hazard_clipped(model_data_clipped_path: Path) -> xr.Dataset:
    p = Path(
        model_data_clipped_path,
        "hazard.nc",
    )
    assert p.is_file()
    ds = open_nc(p, mask_and_scale=False)
    assert len(ds.data_vars) != 0
    return ds


## OSM data
@pytest.fixture(scope="session")
@check_connection()
def osm_data_path() -> Path:
    # Fetch the data
    p = fetch_data("osmnx", cache_dir=CACHE_DIR)
    assert len(list(p.iterdir())) != 0
    return p


## Models and mocked objects
@pytest.fixture
def model(
    tmp_path: Path,
    build_data_catalog_path: Path,
    global_data_catalog_path: Path,
) -> FIATModel:
    model = FIATModel(
        tmp_path,
        mode="w",
        data_libs=[build_data_catalog_path, global_data_catalog_path],
    )
    return model


@pytest.fixture
def model_with_region(
    model: FIATModel,
    build_region_small: Path,
) -> FIATModel:
    model.set_region(build_region_small)
    return model


## Extra data structures
@pytest.fixture
def box_geometry() -> gpd.GeoDataFrame:
    geom = gpd.GeoDataFrame(
        geometry=[box(4.355, 52.035, 4.365, 52.045)],
        crs=4326,
    )
    return geom


@pytest.fixture
def config_dummy(tmp_path: Path) -> dict:
    data = {
        "type": "geom",
        "threads": 4,
        "hazard": {
            "file": Path(tmp_path, "foo.nc"),
            "rp": [1, 2, 3],
            "variables": [{"name": "a", "type": "water_depth", "rp": 1}],
        },
        "vulnerability": {
            "file": Path("foo.csv"),
            "variables": [
                {
                    "name": "default",
                    "method": "flood.depth",
                    "types": {"depth_default": "water_depth"},
                }
            ],
        },
        "exposure": [{"file": "foo.fgb", "variables": {"vulnerability": "default"}}],
    }
    return data


@pytest.fixture
def exposure_cost_dict() -> dict[str, float]:
    data = {
        "residential_structure": 294.910236432,
        "residential_content": 147.455118216,
        "commercial_structure": 319.45019868,
        "commercial_content": 319.45019868,
        "industrial_structure": 217.356427584,
        "industrial_content": 326.034641376,
        "unknown_structure": 277.238954232,
        "unknown_content": 249.51505880880003,
    }
    return data


@pytest.fixture
def exposure_cost_link() -> pd.DataFrame:
    df = pd.DataFrame(
        data={
            "object_type": ["residential", "commercial", "industrial", "unknown"],
            "cost_type": ["residential", "commercial", "industrial", "unknown"],
        }
    )
    return df


@pytest.fixture
def vector_grid(exposure_vector_clipped: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    bbox = exposure_vector_clipped.total_bounds
    # Get the sizes in y and x directions
    dy = bbox[3] - bbox[1]
    dx = bbox[2] - bbox[0]
    res = 100

    # Setup the vector grid
    vg: gpd.GeoDataFrame = full_from_transform(
        transform=(res, 0.0, bbox[0], 0.0, -res, bbox[3]),
        shape=(math.ceil(dy / res), math.ceil(dx / res)),
        crs=exposure_vector_clipped.crs,
    ).raster.vector_grid()
    vg[SQUARE__ID] = range(len(vg))

    # Return the vector grid
    return vg
