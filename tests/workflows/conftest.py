from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from hydromt import DataCatalog
from hydromt.gis import full


## Data from the data catalog
@pytest.fixture
def buildings_data(
    build_data_catalog: DataCatalog, build_region_small: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    gdf = build_data_catalog.get_geodataframe("buildings", geom=build_region_small)
    return gdf


@pytest.fixture(scope="session")
def buildings_link_table(build_data_catalog: DataCatalog) -> pd.DataFrame:
    df = build_data_catalog.get_dataframe("buildings_link")
    return df


@pytest.fixture(scope="session")
def exposure_cost_table(global_data_catalog: DataCatalog) -> pd.DataFrame:
    df = global_data_catalog.get_dataframe("jrc_damage")
    return df


@pytest.fixture
def exposure_grid_data_ind(
    build_data_catalog: DataCatalog, build_region_small: gpd.GeoDataFrame
) -> xr.DataArray:
    ds = build_data_catalog.get_rasterdataset(
        "industrial_content",
        geom=build_region_small,
    )
    return ds


@pytest.fixture
def exposure_grid_link(build_data_catalog: DataCatalog) -> pd.DataFrame:
    df = build_data_catalog.get_dataframe("exposure_grid_link")
    return df


@pytest.fixture
def hazard_event_data(
    build_data_catalog: DataCatalog, build_region_small: gpd.GeoDataFrame
) -> xr.DataArray:
    ds = build_data_catalog.get_rasterdataset("flood_event", geom=build_region_small)
    return ds


@pytest.fixture
def hazard_event_data_highres(
    build_data_catalog: DataCatalog,
    build_region_small: gpd.GeoDataFrame,
) -> xr.DataArray:
    ds = build_data_catalog.get_rasterdataset(
        "flood_event_highres",
        geom=build_region_small,
    )
    return ds


@pytest.fixture
def vulnerability_data(global_data_catalog: DataCatalog) -> pd.DataFrame:
    df = global_data_catalog.get_dataframe("jrc_curves")
    assert len(df) != 0
    return df


@pytest.fixture
def vulnerability_data_row_oriented(vulnerability_data) -> pd.DataFrame:
    vulnerability_data = vulnerability_data.transpose()
    vulnerability_data.columns = vulnerability_data.iloc[0]
    vulnerability_data.drop(0, inplace=True)
    return vulnerability_data


@pytest.fixture
def vulnerability_linking(global_data_catalog: DataCatalog) -> pd.DataFrame:
    df = global_data_catalog.get_dataframe("jrc_curves_link")
    assert len(df) != 0
    return df


@pytest.fixture
def vulnerability_linking_alt(global_data_catalog: DataCatalog) -> pd.DataFrame:
    df = global_data_catalog.get_dataframe("jrc_curves_link_alt")
    assert len(df) != 0
    return df


## Data from a prebuild model
@pytest.fixture
def exposure_geom_data_alt(model_data_clipped_path: Path) -> gpd.GeoDataFrame:
    p = Path(model_data_clipped_path, "exposure", "buildings_alt.fgb")
    assert p.is_file()
    gdf = gpd.read_file(p)
    assert len(gdf) != 0
    return gdf


@pytest.fixture
def exposure_geom_data_link(
    exposure_vector_clipped_for_damamge: gpd.geodataframe,
) -> gpd.GeoDataFrame:
    exposure_vector_clipped_for_damamge.drop(
        [
            "object_id",
            "fn_damage_structure",
            "fn_damage_content",
        ],
        axis=1,
        inplace=True,
    )
    return exposure_vector_clipped_for_damamge


@pytest.fixture(scope="session")
def vulnerability_curves_alt(model_data_path: Path) -> pd.DataFrame:
    p = Path(model_data_path, "vulnerability", "curves_alt.csv")
    assert p.is_file()
    df = pd.read_csv(p)
    assert len(df) != 0
    return df


@pytest.fixture(scope="session")
def vulnerability_identifiers_alt(model_data_path: Path) -> pd.DataFrame:
    p = Path(model_data_path, "vulnerability", "curves_alt_id.csv")
    assert p.is_file()
    df = pd.read_csv(p)
    assert len(df) != 0
    return df


## Extra data structure
@pytest.fixture(scope="session")
def rotated_grid() -> xr.DataArray:
    # Create coordinates
    yc = xr.DataArray(data=np.array([[2.0, 1.5], [1.0, 0.5]]), dims=["y", "x"])
    xc = xr.DataArray(data=np.array([[0.5, 1.5], [0.0, 1.0]]), dims=["y", "x"])
    # Build using 'full' from core
    da = full(coords={"yc": yc, "xc": xc}, nodata=-1, crs=4326)
    return da
